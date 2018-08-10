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

from neutronclient.common import exceptions

from heat.common import exception
from heat.common.i18n import _
from heat.engine import constraints
from heat.engine import properties
from heat.engine.resources.openstack.neutron import neutron
from heat.engine import support
from heat.engine import translation


class TapFlow(neutron.NeutronResource):
    """A resource for neutron tap-as-a-service tap-flow.

    This plug-in requires neutron-taas. So to enable this
    plug-in, install this library and restart the heat-engine.

    A Tap-Flow represents the port from which the traffic needs
    to be mirrored.
    """

    required_service_extension = 'taas'

    entity = 'tap_flow'

    support_status = support.SupportStatus(version='7.0.0')

    PROPERTIES = (
        NAME, DESCRIPTION, PORT, TAP_SERVICE, DIRECTION
        ) = (
        'name', 'description', 'port', 'tap_service', 'direction',
    )

    properties_schema = {
        NAME: properties.Schema(
            properties.Schema.STRING,
            _('Name for the Tap-Flow.'),
            update_allowed=True
        ),
        DESCRIPTION: properties.Schema(
            properties.Schema.STRING,
            _('Description for the Tap-Flow.'),
            update_allowed=True
        ),
        PORT: properties.Schema(
            properties.Schema.STRING,
            _('ID or name of the tap-flow neutron port.'),
            constraints=[constraints.CustomConstraint('neutron.port')],
            required=True,
        ),
        TAP_SERVICE: properties.Schema(
            properties.Schema.STRING,
            _('ID or name of the neutron tap-service.'),
            constraints=[constraints.CustomConstraint('neutron.tap_service')],
            required=True,
        ),
        DIRECTION: properties.Schema(
            properties.Schema.STRING,
            _('The Direction to capture the traffic on.'),
            default='BOTH',
            constraints=[
                constraints.AllowedValues(['IN', 'OUT', 'BOTH']),
            ]
        ),
    }

    def translation_rules(self, props):
        return [
            translation.TranslationRule(
                props,
                translation.TranslationRule.RESOLVE,
                [self.PORT],
                client_plugin=self.client_plugin(),
                finder='find_resourceid_by_name_or_id',
                entity='port'
            ),
            translation.TranslationRule(
                props,
                translation.TranslationRule.RESOLVE,
                [self.TAP_SERVICE],
                client_plugin=self.client_plugin(),
                finder='find_resourceid_by_name_or_id',
                entity='tap_service'
            )
        ]

    def _show_resource(self):
        return self.client_plugin().show_taas_resource('tap_flow',
                                                       self.resource_id)

    def handle_create(self):
        props = self.prepare_properties(self.properties,
                                        self.physical_resource_name())
        to_client = {}
        to_client['name'] = props.get(self.NAME)
        to_client['description'] = props.get(self.DESCRIPTION)
        to_client['source_port'] = props.get(self.PORT)
        to_client['tap_service_id'] = props.get(self.TAP_SERVICE)
        to_client['direction'] = props.get(self.DIRECTION)
        tap_flow = self.client_plugin().create_taas_resource('tap_flow',
                                                             to_client)
        self.resource_id_set(tap_flow['id'])

    def handle_update(self, json_snippet, tmpl_diff, prop_diff):
        if prop_diff:
            self.prepare_update_properties(prop_diff)
            self.client_plugin().update_taas_resource('tap_flow', prop_diff,
                                                      self.resource_id)

    def handle_delete(self):
        if self.resource_id is None:
            return
        with self.client_plugin().ignore_not_found:
                self.client_plugin().delete_taas_resource('tap_flow',
                                                          self.resource_id)

    def check_create_complete(self, data):
        return self.client_plugin().check_taas_resource_status(
            'tap_flow', self.resource_id)

    def check_update_complete(self, prop_diff):
        if prop_diff:
            return self.client_plugin().check_taas_resource_status(
                'tap_flow', self.resource_id)
        return True

    def check_delete_complete(self, data):
        if self.resource_id is None:
            return True

        try:
            try:
                if self.client_plugin().check_taas_resource_status(
                        'tap_flow', self.resource_id):
                    self.client_plugin().delete_taas_resource('tap_flow',
                                                              self.resource_id)
            except exception.ResourceInError:
                # Still try to delete loadbalancer in error state
                self.client_plugin().delete_taas_resource('tap_flow',
                                                          self.resource_id)
        except exceptions.NotFound:
            # Resource is gone
            return True

        return False


def resource_mapping():
    return {
        'OS::Neutron::TapFlow': TapFlow,
    }
