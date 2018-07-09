# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from . import metrics as aci_metrics
from . import helpers
from . import exceptions


class Capacity:
    """
    Collect capacity metrics from the APIC
    """

    def __init__(self, api, instance, check_tags=None, gauge=None, log=None):
        self.api = api
        self.instance = instance
        self.user_tags = instance.get('tags', [])
        self.check_tags = check_tags
        if not self.check_tags:
            self.check_tags = []

        # grab some functions from the check
        self.gauge = gauge
        self.log = log

    def collect(self):
        self.log.info("collecting capacity data")
        try:
            self._get_contexts()
        except exceptions.APIConnectionException, exceptions.APIParsingException:
            # all should fail independently
            pass
        try:
            self._get_apic_capacity_limits()
        except exceptions.APIConnectionException, exceptions.APIParsingException:
            # all should fail independently
            pass
        try:
            self._get_apic_capacity_metrics()
        except exceptions.APIConnectionException, exceptions.APIParsingException:
            # all should fail independently
            pass
        try:
            self._get_eqpt_capacity()
        except exceptions.APIConnectionException, exceptions.APIParsingException:
            # all should fail independently
            pass
        self.log.info("finished collecting capacity data")

    def _get_eqpt_capacity(self):
        for c, metric_dict in aci_metrics.EQPT_CAPACITY_METRICS.iteritems():
            data = self.api.get_eqpt_capacity(c)
            for d in data:
                dn = d.get('attributes', {}).get('dn', '')
                children = d.get('children', [])
                tags = helpers.parse_capacity_tags(dn)
                tags += self.user_tags + self.check_tags  # TODO This is a bug fix. it used to keep appending same tags in the loop
                hostname = helpers.get_hostname_from_dn(dn)
                for child in children:
                    attr = child.get(c, {}).get('attributes', {})
                    for cisco_metric, dd_metric in metric_dict.iteritems():
                        value = attr.get(cisco_metric, 0)
                        self.gauge(dd_metric, value, tags=tags, hostname=hostname)

    def _get_contexts(self):
        for c, metric_dict in aci_metrics.CAPACITY_CONTEXT_METRICS.iteritems():
            dd_metric = metric_dict.get("metric_name")
            utilized_metric_name = dd_metric + ".utilized"
            # These Values are, for some reason, hardcoded in the UI
            # it is not api addressable
            # we need them to make it addressable
            # for the demo, we're hardcoding it
            limit_value = metric_dict.get("limit_value")
            limit_metric_name = dd_metric + ".limit"
            data = self.api.get_capacity_contexts(c)
            for d in data:
                attr = d.get('ctxClassCnt', {}).get('attributes', {})
                dn = attr.get('dn', '')
                tags = helpers.parse_capacity_tags(dn)
                hostname = helpers.get_hostname_from_dn(dn)
                value = attr.get('count', 0)
                tags += self.check_tags + self.user_tags
                self.gauge(utilized_metric_name, value, tags=tags, hostname=hostname)
                self.gauge(limit_metric_name, limit_value, tags=tags, hostname=hostname)

    def _get_apic_capacity_limits(self):
        tags = self.user_tags + self.check_tags
        data = self.api.get_apic_capacity_limits()
        for d in data:
            attr = d.get('fvcapRule', {}).get('attributes', {})
            value = attr.get('constraint', 0)
            subj = attr.get('subj')
            dd_metric = aci_metrics.APIC_CAPACITY_LIMITS.get(subj)
            if dd_metric:
                self.gauge(dd_metric, value, tags=tags)

    def _get_apic_capacity_metrics(self):
        tags = self.user_tags + self.check_tags
        for c, opts in aci_metrics.APIC_CAPACITY_METRICS.iteritems():
            dd_metric = opts.get("metric_name")
            data = self.api.get_apic_capacity_metrics(c, query=opts.get("query_string"))
            if c == "fabricNode":
                value = len(data)
                self.gauge(dd_metric, value, tags=tags)
            else:
                for d in data:
                    attr = d.get('moCount', {}).get('attributes', {})
                    value = attr.get('count', 0)
                    self.gauge(dd_metric, value, tags=tags)
