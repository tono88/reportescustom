/** @odoo-module **/
import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { Domain } from "@web/core/domain";
import { DomainSelector } from "@web/core/domain_selector/domain_selector";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

class JsonDomainField extends Component {
  static template = "tecnodyne_dashboard.JsonDomain";
  static components = { DomainSelector };
  static props = { ...standardFieldProps };
  get domain() {
    try {
      return new Domain(
        JSON.parse(this.props.record.data[this.props.name] || "[]"),
      ).toString();
    } catch {
      return "[]";
    }
  }
  update(value) {
    this.props.record.update({
      [this.props.name]: JSON.stringify(new Domain(value).toList()),
    });
  }
}
registry.category("fields").add("td_json_domain", {
  component: JsonDomainField,
  supportedTypes: ["text"],
});
