# Copyright 2017 VMware, Inc.
# All Rights Reserved
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
#

import abc
import six

from vmware_nsxlib.v3 import policy_constants

TENANTS_PATH_PATTERN = "%s/"
DOMAINS_PATH_PATTERN = TENANTS_PATH_PATTERN + "domains/"
COMM_PROF_PATH_PATTERN = TENANTS_PATH_PATTERN + "communication-profiles/"
SERVICES_PATH_PATTERN = TENANTS_PATH_PATTERN + "services/"


@six.add_metaclass(abc.ABCMeta)
class ResourceDef(object):
    def __init__(self):
        self.tenant = None
        self.id = None
        self.name = None
        self.description = None
        self.parent_ids = None
        self.body = {}

    def get_obj_dict(self):
        body = {'_revision': 0,
                'display_name': self.name,
                'description': self.description}
        if self.id:
            body['id'] = self.id
        return body

    @abc.abstractproperty
    def path_pattern(self):
        pass

    def get_section_path(self):
        return self.path_pattern % self.parent_ids

    def get_resource_path(self):
        if self.id:
            return self.get_section_path() + self.id
        return self.get_section_path()

    def get_resource_full_path(self):
        return '/' + self.get_resource_path()

    @property
    def get_last_section_dict_key(self):
        last_section = self.path_pattern.split("/")[-2]
        return last_section.replace('-', '_')

    @staticmethod
    def sub_entries_path():
        pass

    def update_attributes_in_body(self, body, **kwargs):
        self.body = body
        for key, value in six.iteritems(kwargs):
            if value is not None:
                if key == 'name':
                    self.body['display_name'] = value
                else:
                    self.body[key] = value
        entries_path = self.sub_entries_path()
        # make sure service entries are there
        if entries_path and entries_path not in self.body:
            self.body[entries_path] = []

    @classmethod
    def get_single_entry(cls, obj_body):
        """Return the single sub-entry from the object body.

        If there are no entries, or more than 1 - return None.
        """
        entries_path = cls.sub_entries_path()
        if not entries_path:
            # This sub class doesn't support this
            return None

        if (entries_path not in obj_body or
            len(obj_body[entries_path]) != 1):
            return None

        return obj_body[entries_path][0]


class DomainDef(ResourceDef):

    def __init__(self,
                 domain_id=None,
                 name=None,
                 description=None,
                 tenant=policy_constants.POLICY_INFRA_TENANT):
        super(DomainDef, self).__init__()
        self.tenant = tenant
        self.id = domain_id
        self.name = name
        self.description = description
        self.parent_ids = (tenant)

    @property
    def path_pattern(self):
        return DOMAINS_PATH_PATTERN


class Condition(object):
    def __init__(self, value, key=policy_constants.CONDITION_KEY_TAG,
                 member_type=policy_constants.CONDITION_MEMBER_PORT,
                 operator=policy_constants.CONDITION_OP_EQUALS):
        self.value = value
        self.key = key
        self.member_type = member_type
        self.operator = operator

    def get_obj_dict(self):
        return {'resource_type': 'Condition',
                'member_type': self.member_type,
                'key': self.key,
                'value': self.value,
                'operator': self.operator}


class GroupDef(ResourceDef):
    def __init__(self,
                 domain_id=None,
                 group_id=None,
                 name=None,
                 description=None,
                 conditions=None,
                 tenant=policy_constants.POLICY_INFRA_TENANT):
        super(GroupDef, self).__init__()
        self.tenant = tenant
        self.id = group_id
        self.name = name
        self.description = description
        self.parent_ids = (tenant, domain_id)
        if conditions and isinstance(conditions, Condition):
            self.conditions = [conditions]
        else:
            self.conditions = conditions

    @property
    def path_pattern(self):
        return DOMAINS_PATH_PATTERN + "%s/groups/"

    def get_obj_dict(self):
        body = super(GroupDef, self).get_obj_dict()
        if self.conditions:
            body['expression'] = [condition.get_obj_dict()
                                  for condition in self.conditions]
        return body

    def update_attributes_in_body(self, body, **kwargs):
        # Fix params that need special conversions
        if kwargs.get('conditions') is not None:
            body['expression'] = [cond.get_obj_dict()
                                  for cond in kwargs['conditions']]
            del kwargs['conditions']
        super(GroupDef, self).update_attributes_in_body(body, **kwargs)


class ServiceDef(ResourceDef):
    def __init__(self,
                 service_id=None,
                 name=None,
                 description=None,
                 tenant=policy_constants.POLICY_INFRA_TENANT):
        super(ServiceDef, self).__init__()
        self.tenant = tenant
        self.id = service_id
        self.name = name
        self.description = description
        self.parent_ids = (tenant)
        self.service_entries = []

    @property
    def path_pattern(self):
        return SERVICES_PATH_PATTERN

    def get_obj_dict(self):
        body = super(ServiceDef, self).get_obj_dict()
        body['service_entries'] = [entry.get_obj_dict()
                                   for entry in self.service_entries]
        return body

    @staticmethod
    def sub_entries_path():
        return L4ServiceEntryDef().get_last_section_dict_key


class L4ServiceEntryDef(ResourceDef):
    def __init__(self,
                 service_id=None,
                 service_entry_id=None,
                 name=None,
                 description=None,
                 protocol=policy_constants.TCP,
                 dest_ports=None,
                 tenant=policy_constants.POLICY_INFRA_TENANT):
        super(L4ServiceEntryDef, self).__init__()
        self.tenant = tenant
        self.id = service_entry_id
        self.name = name
        self.description = description
        self.protocol = protocol.upper()
        self.dest_ports = dest_ports
        self.parent_ids = (tenant, service_id)

    @property
    def path_pattern(self):
        return SERVICES_PATH_PATTERN + "%s/service-entries/"

    def get_obj_dict(self):
        body = super(L4ServiceEntryDef, self).get_obj_dict()
        body['resource_type'] = 'L4PortSetServiceEntry'
        body['l4_protocol'] = self.protocol
        body['destination_ports'] = self.dest_ports
        return body

    def update_attributes_in_body(self, body, **kwargs):
        # Fix params that need special conversions
        if kwargs.get('protocol') is not None:
            body['l4_protocol'] = kwargs['protocol'].upper()
            del kwargs['protocol']
        if kwargs.get('dest_ports') is not None:
            body['destination_ports'] = kwargs['dest_ports']
            del kwargs['dest_ports']
        super(L4ServiceEntryDef, self).update_attributes_in_body(
            body, **kwargs)


class CommunicationProfileDef(ResourceDef):
    def __init__(self,
                 profile_id=None,
                 name=None,
                 description=None,
                 tenant=policy_constants.POLICY_INFRA_TENANT):
        super(CommunicationProfileDef, self).__init__()
        self.tenant = tenant
        self.id = profile_id
        self.name = name
        self.description = description
        self.parent_ids = (tenant)

    @property
    def path_pattern(self):
        return COMM_PROF_PATH_PATTERN

    def get_obj_dict(self):
        body = super(CommunicationProfileDef, self).get_obj_dict()
        body['communication_profile_entries'] = []
        return body

    @staticmethod
    def sub_entries_path():
        entryDef = CommunicationProfileEntryDef()
        return entryDef.get_last_section_dict_key

    def update_attributes_in_body(self, body, **kwargs):
        super(CommunicationProfileDef, self).update_attributes_in_body(
            body, **kwargs)
        # make sure entries are there
        entries_path = self.sub_entries_path()
        if entries_path not in self.body:
            self.body[entries_path] = []


class CommunicationProfileEntryDef(ResourceDef):
    def __init__(self,
                 profile_id=None,
                 profile_entry_id=None,
                 name=None,
                 description=None,
                 services=None,
                 action=policy_constants.ACTION_ALLOW,
                 tenant=policy_constants.POLICY_INFRA_TENANT):
        super(CommunicationProfileEntryDef, self).__init__()
        self.tenant = tenant
        self.id = profile_entry_id
        self.name = name
        self.description = description
        self.services = services
        self.action = action.upper()
        self.parent_ids = (tenant, profile_id)

    @property
    def path_pattern(self):
        return COMM_PROF_PATH_PATTERN + "%s/communication-profile-entries/"

    def get_obj_dict(self):
        body = super(CommunicationProfileEntryDef, self).get_obj_dict()
        body['services'] = self.services
        body['action'] = self.action
        return body

    def update_attributes_in_body(self, body, **kwargs):
        if kwargs.get('action') is not None:
            body['action'] = kwargs['action'].upper()
            del kwargs['action']
        super(CommunicationProfileEntryDef, self).update_attributes_in_body(
            body, **kwargs)


class CommunicationMapDef(ResourceDef):
    def __init__(self,
                 domain_id=None,
                 tenant=policy_constants.POLICY_INFRA_TENANT):
        super(CommunicationMapDef, self).__init__()
        self.tenant = tenant
        self.parent_ids = (tenant, domain_id)

    @property
    def path_pattern(self):
        return (DOMAINS_PATH_PATTERN + "%s/communication-map/")


class CommunicationMapEntryDef(ResourceDef):
    def __init__(self,
                 domain_id=None,
                 map_id=None,
                 sequence_number=None,
                 source_groups=None,
                 dest_groups=None,
                 profile_id=None,
                 name=None,
                 description=None,
                 tenant=policy_constants.POLICY_INFRA_TENANT):
        super(CommunicationMapEntryDef, self).__init__()
        self.tenant = tenant
        self.domain_id = domain_id
        self.id = map_id
        self.name = name
        self.description = description
        self.sequence_number = sequence_number

        self.source_groups = self.get_groups_path(domain_id, source_groups)
        self.dest_groups = self.get_groups_path(domain_id, dest_groups)
        self.profile_path = self.get_profile_path(
            profile_id) if profile_id else None
        self.parent_ids = (tenant, domain_id)

    # convert groups and communication profile to full path
    def get_groups_path(self, domain_id, group_ids):
        if not group_ids:
            return [policy_constants.ANY_GROUP]
        return [GroupDef(domain_id,
                         group_id,
                         tenant=self.tenant).get_resource_full_path()
                for group_id in group_ids]

    def get_profile_path(self, profile_id):
        return CommunicationProfileDef(
            profile_id,
            tenant=self.tenant).get_resource_full_path()

    @property
    def path_pattern(self):
        return (DOMAINS_PATH_PATTERN +
                "%s/communication-map/communication-entries/")

    def get_obj_dict(self):
        body = super(CommunicationMapEntryDef, self).get_obj_dict()
        body['source_groups'] = self.source_groups
        body['destination_groups'] = self.dest_groups
        body['sequence_number'] = self.sequence_number
        body['communication_profile_path'] = self.profile_path
        return body

    def update_attributes_in_body(self, body, **kwargs):
        # Fix params that need special conversions
        if kwargs.get('profile_id') is not None:
            profile_path = self.get_profile_path(kwargs['profile_id'])
            body['communication_profile_path'] = profile_path
            del kwargs['profile_id']

        if kwargs.get('dest_groups') is not None:
            groups = self.get_groups_path(
                self.domain_id, kwargs['dest_groups'])
            body['destination_groups'] = groups
            del kwargs['dest_groups']

        if kwargs.get('source_groups') is not None:
            groups = self.get_groups_path(
                self.domain_id, kwargs['source_groups'])
            body['source_groups'] = groups
            del kwargs['source_groups']

        super(CommunicationMapEntryDef, self).update_attributes_in_body(
            body, **kwargs)


class EnforcementPointDef(ResourceDef):

    def __init__(self, ep_id=None,
                 name=None,
                 description=None,
                 ip_address=None,
                 username=None,
                 password=None,
                 ep_type='NSXT',
                 tenant=policy_constants.POLICY_INFRA_TENANT):
        super(EnforcementPointDef, self).__init__()
        self.id = ep_id
        self.name = name
        self.description = description
        self.tenant = tenant
        self.type = ep_type
        self.username = username
        self.password = password
        self.ip_address = ip_address
        self.parent_ids = (tenant)

    @property
    def path_pattern(self):
        return (TENANTS_PATH_PATTERN +
                'deploymentzones/default-deployment-zone/enforcementpoints/')

    def get_obj_dict(self):
        body = super(EnforcementPointDef, self).get_obj_dict()
        body['id'] = self.id
        body['connection_info'] = [{'fqdn': 'abc',
                                    'thumbprint':
                                    policy_constants.DEFAULT_THUMBPRINT,
                                    'username': self.username,
                                    'password': self.password,
                                    'ip_address': self.ip_address,
                                    'resource_type': 'NSXTConnectionInfo'}]
        body['enforcement_type'] = self.type
        body['resource_type'] = 'EnforcementPoint'
        return body

    def update_attributes_in_body(self, body, **kwargs):
        # Fix params that need special conversions
        if body.get('connection_info'):
            body['connection_info'][0]['resource_type'] = 'NSXTConnectionInfo'
            if kwargs.get('username') is not None:
                body['connection_info'][0]['username'] = kwargs['username']
                del kwargs['username']

            if kwargs.get('password') is not None:
                body['connection_info'][0]['password'] = kwargs['password']
                del kwargs['password']

            if kwargs.get('ip_address') is not None:
                body['connection_info'][0]['ip_address'] = kwargs['ip_address']
                del kwargs['ip_address']

        super(EnforcementPointDef, self).update_attributes_in_body(
            body, **kwargs)


# Currently assumes one deployment point per id
class DeploymentMapDef(ResourceDef):

    def __init__(self, map_id=None,
                 name=None,
                 description=None,
                 domain_id=None,
                 ep_id=None,
                 tenant=policy_constants.POLICY_INFRA_TENANT):
        super(DeploymentMapDef, self).__init__()
        self.id = map_id
        self.name = name
        self.description = description
        # convert enforcement point id to path
        self.ep_path = EnforcementPointDef(
            ep_id,
            tenant=tenant).get_resource_full_path() if ep_id else None
        self.domain_path = DomainDef(
            domain_id,
            tenant=tenant).get_resource_full_path() if domain_id else None
        self.tenant = tenant
        self.parent_ids = (tenant)

    @property
    def path_pattern(self):
        return (TENANTS_PATH_PATTERN + 'domaindeploymentmap/')

    def get_obj_dict(self):
        body = super(DeploymentMapDef, self).get_obj_dict()
        body['id'] = self.id
        body['domain_path'] = self.domain_path
        body['enforcement_point_paths'] = [self.ep_path]
        return body

    def update_attributes_in_body(self, body, **kwargs):
        # Fix params that need special conversions
        if kwargs.get('domain_id') is not None:
            domain_id = kwargs.get('domain_id')
            domain_path = DomainDef(
                domain_id, tenant=self.tenant).get_resource_full_path()
            body['domain_path'] = domain_path
            del kwargs['domain_id']

        if kwargs.get('ep_id') is not None:
            ep_id = kwargs.get('ep_id')
            ep_path = EnforcementPointDef(
                ep_id, tenant=self.tenant).get_resource_full_path()
            body['enforcement_point_paths'] = [ep_path]
            del kwargs['ep_id']

        super(DeploymentMapDef, self).update_attributes_in_body(
            body, **kwargs)


class NsxPolicyApi(object):

    def __init__(self, client):
        self.client = client

    def create(self, resource_def):
        path = resource_def.get_resource_path()
        return self.client.update(path, resource_def.get_obj_dict())

    def create_with_parent(self, parent_def, resource_def):
        path = parent_def.get_resource_path()
        body = parent_def.get_obj_dict()
        if isinstance(resource_def, list):
            child_dict_key = resource_def[0].get_last_section_dict_key
            body[child_dict_key] = [r.get_obj_dict() for r in resource_def]
        else:
            child_dict_key = resource_def.get_last_section_dict_key
            body[child_dict_key] = [resource_def.get_obj_dict()]
        return self.client.update(path, body)

    def delete(self, resource_def):
        path = resource_def.get_resource_path()
        self.client.delete(path)

    def get(self, resource_def):
        path = resource_def.get_resource_path()
        return self.client.get(path)

    def list(self, resource_def):
        path = resource_def.get_section_path()
        return self.client.list(path)

    def update(self, resource_def):
        path = resource_def.get_resource_path()
        body = resource_def.body
        return self.client.update(path, body)
