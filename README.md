# hass-dmp-alarm-panel

Basic integration for DMP alarm panels and HomeAssistant.

## Important Info
This integration is currently in BETA. This means things may break or become unreliable. Additionally, this integration is not a replacement for proper, UL-listed alarm monitoring. This product is not UL listed and should not be used in a production setting as it is still experimental and likely to break.
### Currently Supported Features
* Area status monitoring
* Area arming and disarming
* Door lock/unlock/access
    * Status of the door (open, shut) is not implemented
* Last contact time
    * The panel will check in on a regular basis (set in the settings). If the panel falls offline or the communications are severed, the contact time will not update, and you can alert off of that.

### Unsupported but Planned Features
* Home/Sleep/Away arming
    * DMP implements HSA arming as area arming - so area 1 is perimeter, area 2 is interior, and area 3 is bedrooms. You can sort of get away with HSA arming by setting up 3 areas and arming them depending on if you want H, S, or A; but proper HSA arming is planned
* Trouble Sensor
    * Eventually we'd like to get system troubles monitored on their own Home Assistant sensor entity so that system troubles can be reported to HASS.
* Door/lock Status
    * Currently, all doors are listed as locked all the time regardless of the status of the door. This will eventually be sorted out, but due to the nature of access control doors being locked 99.9% of the time, it just hasn't been implemented due to time.

## Setup
### DMP Alarm
To set up the integration on the alarm side, you need to have your installer (or you if you have the lockout code) perform these steps:
1. In Communication options in the programmer (6653 CMD), create a new communication path with type "NET". Point it to the IP address of your HASS instance. Leave it at port 2001 (unless you've changed it in the config). Test frequency and check in can be however often you fancy. Fail time can be again however long you fancy. Enable all reports (alarm, supv, door access, etc).
2. In Remote Options in the programmer, set a remote key (up to 16 digits). This is not necessary but urged for security sake, as anybody can connect to your panel remotely and disarm it if the remote key is not set. Set Allow Network Remote to Yes and Port to 2001 (or other port as specified in the config).
3. Stop (save the program) and exit.

### HomeAssistant
Modify and add the relevant config sections to your configuration.yaml:

`
dmp:
  listen_port: 2001
  port: 2011
  panels:
    - account_number: 1234
      ip: 1.2.3.4
      remote_key: "0123456789      "

alarm_control_panel:
  - platform: dmp
    area_number: "001"
    area_name: "Basement"
    area_accountnumber: 1234
    # Optional Arm/Disarm Command Zone Mapping Override
    area_disarm_zone: "010203"
    area_home_zone: "01"
    area_away_zone: "010203"
`

Note that the remote key should be space padded. THe account number of the area should match that of the DMP panel it is attached to. This is how the two objects get linked.
Note that the area number should be a string and zero padded to three digits. Eventually this will be fixed so it can accept numbers, but I'm lazy

Clone this repo in the custom_components directory, restart hass, and you're up and running!