#!/usr/bin/env python3
import os
import time
import ipaddress
import requests
import boto3
from botocore.exceptions import ClientError

def validate_ip_format(ip_string, version):
    """Validate IP address format"""
    try:
        if version == 'ipv4':
            ipaddress.IPv4Address(ip_string)
        else:
            ipaddress.IPv6Address(ip_string)
        return True
    except (ValueError, ipaddress.AddressValueError):
        return False

def get_public_ip(ip_version='ipv4'):
    """Fetch public IP address from multiple sources and validate they match"""
    if ip_version == 'ipv4':
        sources = [
            'https://checkip.amazonaws.com',
            'https://ipv4.icanhazip.com'
        ]
    else:
        sources = [
            'https://checkipv6.amazonaws.com',
            'https://ipv6.icanhazip.com'
        ]
    
    ips = []
    for url in sources:
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            ip = response.text.strip()
            if ip:
                print(f"  Fetched {ip_version} from {url.split('/')[2]}: {ip}")
                ips.append(ip)
        except Exception as e:
            print(f"  Failed to fetch from {url.split('/')[2]}: {e}")
            continue
    
    # Need at least 2 sources to validate
    if len(ips) < 2:
        print(f"⚠ Warning: Could not fetch {ip_version} from enough sources for validation")
        return None
    
    # Check if all IPs match
    if len(set(ips)) == 1:
        validated_ip = ips[0]
        if validate_ip_format(validated_ip, ip_version):
            print(f"✓ {ip_version} validated: {validated_ip} (both sources agree)")
            return validated_ip
        else:
            print(f"✗ ERROR: Invalid {ip_version} format received: {validated_ip}")
            print(f"  Skipping Route 53 update for safety.")
            return None
    else:
        print(f"✗ ERROR: {ip_version} mismatch detected! Sources returned different IPs: {ips}")
        print(f"  Skipping Route 53 update for safety. This could indicate:")
        print(f"  - Network issues")
        print(f"  - Compromised IP check service")
        print(f"  - DNS resolution problems")
        return None

def get_current_dns_record(route53, hosted_zone_id, record_name, record_type):
    """Get current DNS record value from Route 53"""
    try:
        response = route53.list_resource_record_sets(
            HostedZoneId=hosted_zone_id,
            StartRecordName=record_name,
            StartRecordType=record_type,
            MaxItems='1'
        )
        
        for record in response['ResourceRecordSets']:
            if record['Name'].rstrip('.') == record_name.rstrip('.') and record['Type'] == record_type:
                if 'ResourceRecords' in record and len(record['ResourceRecords']) > 0:
                    return record['ResourceRecords'][0]['Value']
        return None
    except Exception as e:
        print(f"Error fetching DNS record: {e}")
        return None

def update_route53_record(route53, hosted_zone_id, record_name, record_type, new_ip, ttl):
    """Update Route 53 DNS record"""
    try:
        response = route53.change_resource_record_sets(
            HostedZoneId=hosted_zone_id,
            ChangeBatch={
                'Changes': [{
                    'Action': 'UPSERT',
                    'ResourceRecordSet': {
                        'Name': record_name,
                        'Type': record_type,
                        'TTL': ttl,
                        'ResourceRecords': [{'Value': new_ip}]
                    }
                }]
            }
        )
        print(f"✓ Updated {record_type} record {record_name} to {new_ip}")
        return True
    except ClientError as e:
        print(f"✗ Error updating DNS record: {e}")
        return False

def main():
    # Load configuration from environment variables
    hosted_zone_id = os.getenv('HOSTED_ZONE_ID')
    record_name = os.getenv('RECORD_NAME')
    update_ipv4 = os.getenv('UPDATE_IPV4', 'true').lower() == 'true'
    update_ipv6 = os.getenv('UPDATE_IPV6', 'false').lower() == 'true'
    aws_region = os.getenv('AWS_REGION', 'us-east-1')
    
    # Validate and sanitize numeric inputs
    try:
        check_interval = int(os.getenv('CHECK_INTERVAL', '300'))
        if check_interval < 60:
            print(f"WARNING: CHECK_INTERVAL too low ({check_interval}s), setting to minimum 60s")
            check_interval = 60
        elif check_interval > 86400:
            print(f"WARNING: CHECK_INTERVAL too high ({check_interval}s), setting to maximum 86400s (24h)")
            check_interval = 86400
    except ValueError:
        print("ERROR: CHECK_INTERVAL must be a valid integer, using default 300s")
        check_interval = 300
    
    try:
        ttl = int(os.getenv('TTL', '300'))
        if ttl < 60:
            print(f"WARNING: TTL too low ({ttl}s), setting to minimum 60s")
            ttl = 60
        elif ttl > 86400:
            print(f"WARNING: TTL too high ({ttl}s), setting to maximum 86400s (24h)")
            ttl = 86400
    except ValueError:
        print("ERROR: TTL must be a valid integer, using default 300s")
        ttl = 300
    
    # Validate required configuration
    if not hosted_zone_id or not record_name:
        print("ERROR: HOSTED_ZONE_ID and RECORD_NAME must be set")
        return
    
    if not update_ipv4 and not update_ipv6:
        print("ERROR: At least one of UPDATE_IPV4 or UPDATE_IPV6 must be true")
        return
    
    print(f"Starting Route 53 DNS Updater")
    print(f"Record: {record_name}")
    print(f"Hosted Zone: {hosted_zone_id}")
    print(f"Check interval: {check_interval} seconds")
    print(f"IPv4 updates: {'enabled' if update_ipv4 else 'disabled'}")
    print(f"IPv6 updates: {'enabled' if update_ipv6 else 'disabled'}")
    print("-" * 50)
    
    # Initialize Route 53 client
    route53 = boto3.client('route53', region_name=aws_region)
    
    # Rate limiting: Track last update time per record type
    last_update = {'A': 0, 'AAAA': 0}
    min_update_interval = 30  # Minimum 30 seconds between updates to same record
    
    while True:
        try:
            # Check and update IPv4 (A record)
            if update_ipv4:
                current_ip = get_public_ip('ipv4')
                if current_ip:
                    dns_ip = get_current_dns_record(route53, hosted_zone_id, record_name, 'A')
                    if dns_ip != current_ip:
                        # Rate limiting check
                        time_since_last = time.time() - last_update['A']
                        if time_since_last < min_update_interval:
                            print(f"⚠ Rate limit: Skipping IPv4 update (last update {time_since_last:.0f}s ago)")
                        else:
                            print(f"IPv4 change detected: {dns_ip} → {current_ip}")
                            if update_route53_record(route53, hosted_zone_id, record_name, 'A', current_ip, ttl):
                                last_update['A'] = time.time()
                    else:
                        print(f"IPv4 unchanged: {current_ip}")
            
            # Check and update IPv6 (AAAA record)
            if update_ipv6:
                current_ip = get_public_ip('ipv6')
                if current_ip:
                    dns_ip = get_current_dns_record(route53, hosted_zone_id, record_name, 'AAAA')
                    if dns_ip != current_ip:
                        # Rate limiting check
                        time_since_last = time.time() - last_update['AAAA']
                        if time_since_last < min_update_interval:
                            print(f"⚠ Rate limit: Skipping IPv6 update (last update {time_since_last:.0f}s ago)")
                        else:
                            print(f"IPv6 change detected: {dns_ip} → {current_ip}")
                            if update_route53_record(route53, hosted_zone_id, record_name, 'AAAA', current_ip, ttl):
                                last_update['AAAA'] = time.time()
                    else:
                        print(f"IPv6 unchanged: {current_ip}")
            
        except Exception as e:
            print(f"Error in main loop: {e}")
        
        print(f"Next check in {check_interval} seconds...")
        time.sleep(check_interval)

if __name__ == '__main__':
    main()
