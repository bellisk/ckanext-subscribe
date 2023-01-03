# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2023-01-03

### Added
- Add `ISubscribe` interface, with methods to allow customisation of email
  contents.
- Add `get_activities` method to `ISubscribe` interface, to allow custom
  filtering of the activities we send notifications for.

### Fixed
- Fix sending notifications for non-verified subscriptions.

## [1.0.1] - 2020-02-14

### Changed
- Fix getting weekly notifications when you subscribe to an org or group, and
  one of their datasets changes, even if your scription is not configured to be
  weekly.

## [1.0.0] - 2020-02-07

Initial release
