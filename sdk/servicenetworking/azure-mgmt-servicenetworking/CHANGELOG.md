# Release History

## 1.1.0b1 (2024-09-29)

### Features Added

  - Client `ServiceNetworkingMgmtClient` added operation group `security_policies_interface`
  - Model `TrafficController` added property `security_policies`
  - Model `TrafficController` added property `security_policy_configurations`
  - Model `TrafficControllerUpdate` added property `security_policy_configurations`
  - Added enum `PolicyType`
  - Added model `SecurityPolicy`
  - Added model `SecurityPolicyConfigurations`
  - Added model `SecurityPolicyConfigurationsUpdate`
  - Added model `SecurityPolicyListResult`
  - Added model `SecurityPolicyUpdate`
  - Added model `WafPolicy`
  - Added model `WafPolicyUpdate`
  - Added model `WafSecurityPolicy`
  - Added model `WafSecurityPolicyUpdate`
  - Added model `SecurityPoliciesInterfaceOperations`

## 1.0.0 (2023-11-20)

### Other Changes

  - First GA

## 1.0.0b2 (2023-05-20)

### Features Added

  - Model AssociationUpdate has a new parameter association_type
  - Model AssociationUpdate has a new parameter subnet
  - Model Frontend has a new parameter fqdn

### Breaking Changes

  - Model AssociationUpdate no longer has parameter properties
  - Model Frontend no longer has parameter ip_address_version
  - Model Frontend no longer has parameter mode
  - Model Frontend no longer has parameter public_ip_address
  - Model FrontendUpdate no longer has parameter properties
  - Model TrafficControllerUpdate no longer has parameter properties

## 1.0.0b1 (2023-01-17)

* Initial Release
