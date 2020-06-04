This component has been deprecated since it is now implemented in the standard Home Assistant config as of 109
When upgrading, please remove the custom component and the dynalite should work with almost the same configuration
A few notable changes you may have to make:
1. the strings 'timecover' and 'channelcover' in the config were modified per the Home Assistant standards to 'time_cover' and 'channel_cover'
2. the 'areacreate' and 'areaoverride' configs are no longer valid as areas have to be created in Home Assistant, so please remove them from your config
Other than this, it should be quite similar, but more standard and stable, so I will no longer be maintaining the component
Please let me know if there are any additional issues in converting and I will add them here, as well as any other feedback / suggestions
