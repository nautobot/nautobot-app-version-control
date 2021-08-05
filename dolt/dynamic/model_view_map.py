from nautobot.dcim.tables import cables, devices, devicetypes, power, racks, sites
from nautobot.circuits import tables as circuits_tables
from nautobot.ipam import tables as ipam_tables
from nautobot.tenancy import tables as tenancy_tables
from nautobot.virtualization import tables as virtualization_tables


def content_type_has_diff_view_table(ct):
    # todo: once available, use https://github.com/nautobot/nautobot/issues/747
    return (
        ct.app_label in MODEL_VIEW_TABLES
        and ct.model in MODEL_VIEW_TABLES[ct.app_label]
    )


MODEL_VIEW_TABLES = {
    "dcim": {
        # "baseinterface": devices.BaseInterfaceTable,
        "cable": cables.CableTable,
        # "cabletermination": devices.CableTerminationTable,
        # "componenttemplate": devicetypes.ComponentTemplateTable,
        "consoleport": devices.ConsolePortTable,
        "consoleporttemplate": devicetypes.ConsolePortTemplateTable,
        "consoleserverport": devices.ConsoleServerPortTable,
        "consoleserverporttemplate": devicetypes.ConsoleServerPortTemplateTable,
        "device": devices.DeviceTable,
        "devicebay": devices.DeviceBayTable,
        "devicebaytemplate": devicetypes.DeviceBayTemplateTable,
        # "devicecomponent": devices.DeviceComponentTable,
        # "deviceconsoleport": devices.DeviceConsolePortTable,
        # "deviceconsoleserverport": devices.DeviceConsoleServerPortTable,
        # "devicedevicebay": devices.DeviceDeviceBayTable,
        # "devicefrontport": devices.DeviceFrontPortTable,
        # "deviceimport": devices.DeviceImportTable,
        # "deviceinterface": devices.DeviceInterfaceTable,
        # "deviceinventoryitem": devices.DeviceInventoryItemTable,
        # "devicepoweroutlet": devices.DevicePowerOutletTable,
        # "devicepowerport": devices.DevicePowerPortTable,
        # "devicerearport": devices.DeviceRearPortTable,
        "devicerole": devices.DeviceRoleTable,
        "devicetype": devicetypes.DeviceTypeTable,
        "frontport": devices.FrontPortTable,
        "frontporttemplate": devicetypes.FrontPortTemplateTable,
        "interface": devices.InterfaceTable,
        "interfacetemplate": devicetypes.InterfaceTemplateTable,
        "inventoryitem": devices.InventoryItemTable,
        "manufacturer": devicetypes.ManufacturerTable,
        # "pathendpoint": devices.PathEndpointTable,
        "platform": devices.PlatformTable,
        "powerfeed": power.PowerFeedTable,
        "poweroutlet": devices.PowerOutletTable,
        "poweroutlettemplate": devicetypes.PowerOutletTemplateTable,
        "powerpanel": power.PowerPanelTable,
        "powerport": devices.PowerPortTable,
        "powerporttemplate": devicetypes.PowerPortTemplateTable,
        "rack": racks.RackTable,
        # "rackdetail": racks.RackDetailTable,
        "rackgroup": racks.RackGroupTable,
        "rackreservation": racks.RackReservationTable,
        "rackrole": racks.RackRoleTable,
        "rearport": devices.RearPortTable,
        "rearporttemplate": devicetypes.RearPortTemplateTable,
        "region": sites.RegionTable,
        "site": sites.SiteTable,
        "virtualchassis": devices.VirtualChassisTable,
    },
    "circuits": {
        "circuit": circuits_tables.CircuitTable,
        # "circuittermination": None,
        "circuittype": circuits_tables.CircuitTypeTable,
        "provider": circuits_tables.ProviderTable,
    },
    "ipam": {
        "aggregate": ipam_tables.AggregateTable,
        "ipaddress": ipam_tables.IPAddressTable,
        "prefix": ipam_tables.PrefixTable,
        "rir": ipam_tables.RIRTable,
        "role": ipam_tables.RoleTable,
        "routetarget": ipam_tables.RouteTargetTable,
        "service": ipam_tables.ServiceTable,
        "vlan": ipam_tables.VLANTable,
        "vlangroup": ipam_tables.VLANGroupTable,
        "vrf": ipam_tables.VRFTable,
    },
    "tenancy": {
        "tenantgroup": tenancy_tables.TenantGroupTable,
        "tenant": tenancy_tables.TenantTable,
    },
    "virtualization": {
        "cluster": virtualization_tables.ClusterTypeTable,
        "clustergroup": virtualization_tables.ClusterGroupTable,
        "clustertype": virtualization_tables.ClusterTable,
        "vminterface": virtualization_tables.VMInterfaceTable,
    },
}
