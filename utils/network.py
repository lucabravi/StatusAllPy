import logging
import netifaces


def get_ip_addresses():
    ip_list = []
    interfaces = netifaces.interfaces()
    for interface in interfaces:
        addresses = netifaces.ifaddresses(interface)
        if netifaces.AF_INET in addresses:
            ipv4_addresses = addresses[netifaces.AF_INET]
            for ip in ipv4_addresses:
                ip_address = ip['addr']
                ip_list.append(ip_address)
    logging.info(f'Current host ips: [{",".join(ip_list)}]')
    return ip_list

# Usage
# ip_addresses = get_ip_addresses()
# for ip in ip_addresses:
#     print(ip)
