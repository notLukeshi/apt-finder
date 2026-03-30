# OpenTripPlanner Router Configuration Guide

Use this guide for the router tuning file that gets copied into OTP assets at startup.

## Which file to edit

- **Edit:** `otp-routing/router-config.json`
- **Do not edit:** `otp-routing/assets/router-config.json`
  - This is the runtime copy and gets overwritten when OTP starts

The launcher scripts automatically copy `otp-routing/router-config.json` into `otp-routing/assets/` before OTP is launched.

## Common settings

### `routingDefaults`

These values affect the default feel of routing requests:

- `walkSpeed`: walking speed in m/s
- `bikeSpeed`: cycling speed in m/s
- `transferSlack`: extra transfer buffer in seconds
- `maxWalkDistance`: maximum walk distance to reach transit
- `maxTransferWalkDistance`: maximum walk distance during transfers
- `waitReluctance`: how strongly waiting is penalized
- `walkReluctance`: how strongly walking is penalized
- `bikeReluctance`: how strongly cycling is penalized
- `bikeParkCost`: parking cost in seconds
- `bikeParkTime`: parking time in seconds
- `allowUnknownModes`: whether unknown transport modes are allowed

### `transit.dynamicSearchWindow`

Controls how far OTP searches for transit options:

- `minTripTimeCoefficient`
- `minWinTimeMinutes`
- `maxWinTimeMinutes`

### `updaters`

This project currently leaves real-time updater feeds empty:

```json
"updaters": []
```

## After editing

1. Save your changes to `otp-routing/router-config.json`
2. Restart the OTP launcher
3. Let OTP rebuild the graph if the config affects routing behavior

## Notes

- Some OTP 1.x settings may be deprecated or behave differently under OTP 2.x.
- The runtime copy in `otp-routing/assets/` should never be edited manually.
