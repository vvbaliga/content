from typing import Optional

import urllib3

import demistomock as demisto
from CommonServerPython import *
from CommonServerUserPython import *
import socket

# Disable insecure warnings
urllib3.disable_warnings()

''' GLOBAL VARIABLES'''
INTEGRATION_COMMAND = "cisco-asa"

'''Client'''


class Client(BaseClient):

    def get_all_rules(self, specific_interface: Optional[str] = None, rule_type: str = 'All') -> list:
        """
        Args:
             specific_interface): the name of the interface
             rule_type: All/Global/In

        Returns:
             all rules in Cisco ASA of the specified type/interface
        """
        rules = []  # type: list
        # Get global rules
        if specific_interface is None and rule_type in ['All', 'Global']:
            res = self._http_request('GET', '/api/access/global/rules')
            items = res.get('items', [])
            for item in items:
                item['interface_type'] = "Global"
            rules.extend(items)

        # Get in rules
        if rule_type in ['All', 'In']:
            res = self._http_request('GET', '/api/access/in')
            interfaces = []
            for item in res.get('items', []):
                interface_name = item.get('interface', {}).get('name')
                if interface_name and specific_interface and specific_interface == interface_name:
                    interfaces.append(interface_name)
                if interface_name and not specific_interface:
                    interfaces.append(interface_name)
            for interface in interfaces:
                res = self._http_request('GET', f'/api/access/in/{interface}/rules')
                items = res.get('items', [])
                for item in items:
                    item['interface'] = interface
                    item['interface_type'] = "In"
                rules.extend(items)

        # Get out rules
        if rule_type in ['All', 'Out']:
            res = self._http_request('GET', '/api/access/out')
            interfaces = []
            for item in res.get('items', []):
                interface_name = item.get('interface', {}).get('name')
                if interface_name and specific_interface and specific_interface == interface_name:
                    interfaces.append(interface_name)
                if interface_name and not specific_interface:
                    interfaces.append(interface_name)
            for interface in interfaces:
                res = self._http_request('GET', f'/api/access/out/{interface}/rules')
                items = res.get('items', [])
                for item in items:
                    item['interface'] = interface
                    item['interface_type'] = "Out"
                rules.extend(items)

        return rules

    def rule_action(self, rule_id: str, interface_name: str, interface_type: str, command: str = 'GET',
                    data: dict = None) -> dict:
        """

        Args:
            rule_id: The Rule ID.
            interface_name: the name of the interface.
            interface_type: The type of interface.
            command: What
            data:

        Returns:
            Does the command on the rule.
            Delete - delete rule
            GET - rule info
            PATCH - edit rule
        """
        resp_type = {"GET": "json",
                     "DELETE": "text",
                     "PATCH": "response"
                     }
        if interface_type == "Global":
            rule = self._http_request(command, f'/api/access/global/rules/{rule_id}', resp_type=resp_type[command],
                                      json_data=data)
        if interface_type == "In":
            rule = self._http_request(command, f'/api/access/in/{interface_name}/rules/{rule_id}',
                                      resp_type=resp_type[command], json_data=data)
        if interface_type == 'Out':
            rule = self._http_request(command, f'/api/access/out/{interface_name}/rules/{rule_id}',
                                      resp_type=resp_type[command], json_data=data)
        if command == 'GET':
            rule['interface'] = interface_name
            rule['interface_type'] = interface_type
        return rule

    def create_rule_request(self, interface_type: str, interface_name: str, rule_body: dict) -> dict:
        """

        Args:
            interface_type:
            interface_name:
            rule_body: The information about the rule.

        Returns:
            The new created rule's information.

        """
        if interface_type == "Global":
            res = self._http_request("POST", '/api/access/global/rules', json_data=rule_body, resp_type="response")
        if interface_type == 'In':
            res = self._http_request("POST", '/api/access/in/{}/rules'.format(interface_name), json_data=rule_body,
                                     resp_type="response")
        if interface_type == 'Out':
            res = self._http_request("POST", '/api/access/out/{}/rules'.format(interface_name), json_data=rule_body,
                                     resp_type="response")
        loc = res.headers.get("Location")
        rule = self._http_request('GET', loc[loc.find('/api'):])
        rule['interface'] = interface_name
        rule['interface_type'] = interface_type
        return rule

    def test_command_request(self):
        self._http_request("GET", "/api/aaa/authorization")

    def backup(self, data: dict):
        self._http_request("POST", "/api/backup", json_data=data, resp_type="response")

    def restore(self, data: dict):
        self._http_request("POST", "/api/restore", json_data=data, resp_type='response')


'''HELPER COMMANDS'''


@logger
def raw_to_rules(raw_rules):
    """
    :param raw_rules:
    :return:
    Gets raw rules as received from API and extracts only the relevant fields
    """
    rules = []
    for rule in raw_rules:
        rules.append({"SourceIP": rule.get('sourceAddress', {}).get('value'),
                      "DestIP": rule.get('destinationAddress', {}).get('value'),
                      "IsActive": rule.get('active'),
                      "Interface": rule.get("interface"),
                      "InterfaceType": rule.get("interface_type"),
                      "Remarks": rule.get('remarks'),
                      "Position": rule.get('position'),
                      "ID": rule.get('objectId'),
                      'Permit': rule.get('permit')
                      })
        if not rules[-1].get('SourceIP'):
            rules[-1]['SourceIP'] = rule.get('sourceAddress', {}).get('objectId')
        if not rules[-1].get('DestIP'):
            rules[-1]['DestIP'] = rule.get('destinationAddress', {}).get('objectId')

    return rules


def is_ipv4(ip):
    try:
        socket.inet_aton(ip)
        return True
    except socket.error:
        return False


def is_ipv6(ip):
    try:
        socket.inet_pton(socket.AF_INET6, ip)
        return True
    except socket.error:
        return False


'''COMMANDS'''


@logger
def list_rules_command(client: Client, args):
    """
    :param client:
    :param args: Interface_name - get rules from a specific interface.
                Interface_type - get rules from a specific type of interface.
    :return: hr - human readable, outputs - context, raw

    Returns all rules.
    """
    interface = args.get('interface_name')
    interface_type = args.get('interface_type', 'All')

    try:
        raw_rules = client.get_all_rules(interface, interface_type)  # demisto.getRules() #
        rules = raw_to_rules(raw_rules)
        outputs = {'CiscoASA.Rules(val.ID && val.ID == obj.ID)': rules}
        hr = tableToMarkdown("Rules:", rules, ["ID", "SourceIP", "DestIP", "Permit", "Interface", "InterfaceType",
                                               "IsActive", "Position"])
        return hr, outputs, raw_rules

    except Exception as e:
        if "404" in str(e) and interface:
            raise ValueError("Could not find interface")
        else:
            raise e


@logger
def backup_command(client: Client, args):
    """

    Args:
        client:
        args:

    Returns:
        Creates a backup. Returns a message if backup was created successfully.

    """
    location = "disk0:/" + args.get("backup_name")
    passphrase = args.get("passphrase")
    data = {'location': location}
    if passphrase:
        data['passphrase'] = passphrase

    client.backup(data)
    return f"Created backup successfully in:\nLocation: {location}\nPassphrase: {passphrase}", {}, ""


@logger
def restore_command(client: Client, args):
    location = "disk0:/" + args.get("backup_name")
    passphrase = args.get("passphrase")
    data = {'location': location}
    if passphrase:
        data['passphrase'] = passphrase

    client.restore(data)
    return "Restored backup successfully.", {}, ""


@logger
def rule_by_id_command(client: Client, args):
    rule_id = args.get('rule_id')
    interface_type = args.get('interface_type')
    interface = args.get('interface_name')
    interface = "" if interface_type == "Global" else interface

    raw_rules = client.rule_action(rule_id, interface, interface_type, 'GET')
    rules = raw_to_rules([raw_rules])

    outputs = {'CiscoASA.Rules(val.ID && val.ID == obj.ID)': rules}
    hr = tableToMarkdown("Rule {}:".format(rule_id), rules, ["ID", "SourceIP", "DestIP",
                                                             "Permit", "Interface", "InterfaceType", "IsActive",
                                                             "Position"])
    return hr, outputs, raw_rules


@logger
def create_rule_command(client: Client, args):
    source = args.get('source')
    dest = args.get('destination')
    permit = args.get('permit')
    interface = args.get('interface_name')
    interface_type = args.get('interface_type')

    interface = "" if interface_type == "Global" else interface
    if interface_type != "Global" and not interface:
        raise ValueError("For In/Out interfaces, an interface name is mandatory.")

    remarks = argToList(args.get('remarks'), ',')
    position = args.get('position')
    log_level = args.get('logging_level')
    active = args.get('active', 'True')

    rule_body = {}  # type: dict
    rule_body['sourceService'] = {"kind": "NetworkProtocol",
                                  "value": "ip"}
    # Set up source
    if is_ipv4(source):
        rule_body["sourceAddress"] = {"kind": "IPv4Address",
                                      "value": source}
    if source == 'any':
        rule_body["sourceAddress"] = {"kind": "AnyIPAddress",
                                      "value": "any4"}
    if '/' in source:
        rule_body["sourceAddress"] = {"kind": "IPv4Network",
                                      "value": source}
    if not rule_body.get('sourceAddress'):
        raise ValueError("Source is not a valid IPv4 address/network/any.")

    # Set up dest
    rule_body['destinationService'] = {"kind": "NetworkProtocol",
                                       "value": "ip"}

    if is_ipv4(dest):
        rule_body["destinationAddress"] = {"kind": "IPv4Address",
                                           "value": dest}
    if dest == 'any':
        rule_body["destinationAddress"] = {"kind": "AnyIPAddress",
                                           "value": "any4"}
    if '/' in dest:
        rule_body["destinationAddress"] = {"kind": "IPv4Network",
                                           "value": dest}

    if not rule_body.get('destinationAddress'):
        raise ValueError("Destination is not a valid IPv4 address/network/any.")

    # everything else
    rule_body['permit'] = True if permit == 'True' else False
    rule_body['remarks'] = remarks
    rule_body['active'] = True if active == 'True' else False
    if position:
        rule_body['position'] = position
    if log_level:
        rule_body['ruleLogging'] = {'logStatus': log_level}

    try:
        raw_rule = client.create_rule_request(interface_type, interface, rule_body)
        rules = raw_to_rules([raw_rule])

        outputs = {'CiscoASA.Rules(val.ID && val.ID == obj.ID)': rules}
        hr = tableToMarkdown("Created new rule. ID: {}".format(raw_rule.get('objectId'),),
                             rules, ["ID", "SourceIP", "DestIP", "Permit", "Interface", "InterfaceType", "IsActive",
                                     "Position"])
        return hr, outputs, raw_rule
    except Exception as e:
        if 'DUPLICATE' in str(e):
            raise ValueError("You are trying to create a rule that already exists.")
        if '[500]' in str(e):
            raise ValueError("Could not find interface: {}.".format(interface))
        else:
            raise e


@logger
def delete_rule_command(client: Client, args):
    rule_id = args.get('rule_id')
    interface = args.get('interface_name')
    interface_type = args.get('interface_type')
    try:
        client.rule_action(rule_id, interface, interface_type, 'DELETE')
    except Exception as e:
        if 'Not Found' in str(e):
            raise ValueError(f"Rule {rule_id} does not exist in interface {interface} of type {interface_type}.")

    return f"Rule {rule_id} deleted successfully.", {}, ""


@logger
def edit_rule_command(client: Client, args):
    interface = args.get('interface_name')
    interface_type = args.get('interface_type')
    rule_id = args.get('rule_id')

    interface = "" if interface_type == "Global" else interface

    remarks = argToList(args.get('remarks'), ',')
    position = args.get('position')
    log_level = args.get('logging_level')
    active = args.get('active', 'True')
    source = args.get('source')
    dest = args.get('destination')
    permit = args.get('permit')

    rule_body = {}  # type: dict

    if source:
        rule_body['sourceService'] = {"kind": "NetworkProtocol",
                                      "value": "ip"}
        # Set up source
        if is_ipv4(source):
            rule_body["sourceAddress"] = {"kind": "IPv4Address",
                                          "value": source}
        if source == 'any':
            rule_body["sourceAddress"] = {"kind": "AnyIPAddress",
                                          "value": "any4"}
        if '/' in source:
            rule_body["sourceAddress"] = {"kind": "IPv4Network",
                                          "value": source}

    # Set up dest
    if dest:
        rule_body['destinationService'] = {"kind": "NetworkProtocol",
                                           "value": "ip"}

        if is_ipv4(dest):
            rule_body["destinationAddress"] = {"kind": "IPv4Address",
                                               "value": dest}
        if dest == 'any':
            rule_body["destinationAddress"] = {"kind": "AnyIPAddress",
                                               "value": "any4"}
        if '/' in dest:
            rule_body["destinationAddress"] = {"kind": "IPv4Network",
                                               "value": dest}

    # everything else
    if permit:
        rule_body['permit'] = True if permit == 'True' else False
    if remarks:
        rule_body['remarks'] = remarks
    if active:
        rule_body['active'] = True if active == 'True' else False
    if position:
        rule_body['position'] = position
    if log_level:
        rule_body['ruleLogging'] = {'logStatus': log_level}

    try:
        client.rule_action(rule_id, interface, interface_type, "PATCH", rule_body)
        raw_rule = client.rule_action(rule_id, interface, interface_type, 'GET')
        rules = raw_to_rules([raw_rule])

        outputs = {'CiscoASA.Rules(val.ID && val.ID == obj.ID)': rules}
        hr = tableToMarkdown(f"Edited rule {raw_rule.get('objectId')}",
                             rules, ["ID", "SourceIP", "DestIP", "Permit", "Interface", "InterfaceType", "IsActive",
                                     "Position"])
        return hr, outputs, raw_rule
    except Exception as e:
        if 'DUPLICATE' in str(e):
            raise ValueError("You are trying to create a rule that already exists.")
        if '[500]' in str(e):
            raise ValueError("Could not find interface: {}.".format(interface))
        else:
            raise e


@logger
def test_command(client: Client):
    """
    Args:
        client:

    Returns:
        Runs a random GET API request just to see if successful.
    """

    client.test_command_request()


'''MAIN'''
headers_for_ASAv = {'X-Auth-Token': '661A9A@4096@A1EC@504D0ECDFD77D759AE5694FA138476FF75B21D47'}

def main():
    username = demisto.params().get('credentials').get('identifier')
    password = demisto.params().get('credentials').get('password')
    verify_certificate = not demisto.params().get('insecure', False)
    proxy = demisto.params().get('proxy', False)

    # Remove trailing slash to prevent wrong URL path to service
    server_url = demisto.params()['server'][:-1] \
        if (demisto.params()['server'] and demisto.params()['server'].endswith('/')) else demisto.params()['server']

    commands = {
        f'{INTEGRATION_COMMAND}-list-rules': list_rules_command,
        f'{INTEGRATION_COMMAND}-backup': backup_command,
        f'{INTEGRATION_COMMAND}-get-rule-by-id': rule_by_id_command,
        f'{INTEGRATION_COMMAND}-create-rule': create_rule_command,
        f'{INTEGRATION_COMMAND}-delete-rule': delete_rule_command,
        f'{INTEGRATION_COMMAND}-edit-rule': edit_rule_command
    }

    LOG(f'Command being called is {demisto.command()}')
    try:
        client = Client(server_url, auth=(username, password), verify=verify_certificate, proxy=proxy,
                        headers=headers_for_ASAv)

        if demisto.command() == 'test-module':
            test_command(client)
            demisto.results('ok')
        elif demisto.command() in commands.keys():
            hr, outputs, raw_rules = commands[demisto.command()](client, demisto.args())
            return_outputs(hr, outputs, raw_rules)

    # Log exceptions
    except Exception as e:
        LOG.print_log()
        return_error(f"Failed to execute {demisto.command()} command. Error: {e}")
        raise


if __name__ in ['__main__', 'builtin', 'builtins']:
    main()