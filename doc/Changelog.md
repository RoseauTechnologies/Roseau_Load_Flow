---
myst:
  html_meta:
    description lang=en: |
      Release history of Roseau Load Flow - Three-phase unbalanced load flow solver in a Python API by Roseau
      Technologies.
    keywords lang=en: changelog, solver, simulation, distribution grid, bus, model
    # spellchecker:off
    description lang=fr: |
      Historique des versions de Roseau Load Flow - Solveur d'écoulement de charge triphasé et déséquilibré dans une
      API Python par Roseau Technologies.
    keywords lang=fr: version, solveur, simulation, réseau, électrique, bus
    # spellchecker:on
og:image: https://www.roseautechnologies.com/wp-content/uploads/2024/04/DSCF0091-scaled.webp
og:image:alt: An engineer uses Roseau Load Flow to perform unbalanced electric calculation
og:title: Roseau Load Flow - Unbalanced and multiphase load flow solver
og:description: See what's new in the latest release of Roseau Load Flow !
---

# Changelog

## Unreleased

- {gh-pr}`418` Many improvements to the styles of interactive map plots:

  - Different voltage levels are represented with different marker sizes and line widths. Nominal voltages are used to
    determine the voltage levels automatically. If nominal voltages are not available, they are inferred from the
    transformers and sources
  - Underground lines are dashed while other lines are solid including lines with unknown line type
  - Transformers are now represented with a square icon with a divider in the middle and with both HV and LV buses
    information in the tooltip and popup
  - Sourcers are represented with a bigger square icon
  - If the new parameter `fit_bounds` is set to `True` (default), the bounds of the map will be automatically adjusted
    using `folium.FitOverlays` to fit the network elements.

  Note that the markers of buses, transformers and sources now use the `folium.DivIcon` icon which means the style
  function must now return a style dictionary of the form `{'html': ...}` for these elements.

- {gh-pr}`413` Restore bus and layers to the layer control in the interactive map plot. This was broken in version
  0.13.0.

- {gh-pr}`404` Fix filtering catalogues using compiled regular expressions with newer versions of pandas.

## Version 0.13.1

- Fix a bug where license validation failed when the English (US) language was not installed on the system (observed on
  Linux).

- {gh-pr}`408` Improve the display of C++ code error messages.

## Version 0.13.0

- {gh-pr}`402` Improve the `en.to_graph` method.

  - Add nominal voltage and min/max voltage levels as node attributes.
  - Change the `geom` attribute to be a GeoJSON-like dictionary instead of a shapely geometry object. This makes the
    graph data JSON-serializable and compatible with pyviz plotting.

- {gh-pr}`401` Rename some internal models modules. The models classes are always available as `rlf.<model_name>`.

- {gh-pr}`400` Add `LineParameters.to_sym` method to convert three-phase line parameters to symmetrical components. The
  method returns the symmetrical components: `z0`, `z1`, `y0`, `y1`, and for lines with a neutral wire: `zn`, `zpn`,
  `yn`, `ypn`.

- {gh-pr}`399` Add popup and search functionality to the interactive map plot. `rlf.plotting.plot_interactive_map` now
  accepts `add_tooltips`, `add_popups` and `add_search` arguments to control the display of tooltips, popups and search
  features. These features are enabled by default.

- {gh-pr}`398` Improve the performance of accessing network results as dataframes by up to 20% and serializing a network
  to a dictionary by up to 15%. The improvements are mostly noticeable for large networks or when performing many
  simulations like in a time series analysis.

- {gh-pr}`396` Allow passing a single `FlexibleParameter` object to a constant-power load to be used for all phases.

- {gh-pr}`395` Improve line and bus hover information in interactive map plots. Fix an error in automatic zoom
  calculation when the whole network is on the same longitude or latitude.

- {gh-pr}`394` Add support for musl linux distributions. Also add preliminary support for python 3.14 development
  version and for free-threaded python 3.13t and 3.14t. Full support is waiting on our dependencies to release relevant
  wheels.

- {gh-pr}`393` Use the `uv_build` build backend instead of `hatchling` to build the package.

- {gh-pr}`392` Disconnect a ground connection of a load or source when the load or source is disconnected from the
  network. Add `is_disconnected` property to loads, sources and ground connections to check if the element is
  disconnected. In the future, accessing the bus of a disconnected load or source will return the original bus instead
  of `None`, use `is_disconnected` to check if the load or source is disconnected.

- {gh-pr}`391` {gh-issue}`390` `ElectricalNetwork.to_graph` now returns a multi-graph to preserve parallel edges. It
  also gained a `respect_switches` parameter that can be set to `False` to include open switches in the graph. The
  default value is `True`, which means that open switches are not included in the graph.

- {gh-pr}`389` Add support for open switches. Pass `closed=False` to the `Switch` constructor to create an open switch.
  Call `switch.open()` to open an existing switch and `switch.close()` to close it. `switch.closed` tells if the switch
  is closed or not. The switch is closed by default.

- {gh-pr}`388` {gh-issue}`378` Add `ElectricalNetwork.tool_data` to attach tool-specific data to the electrical network.
  The data is written to the JSON file when saving the network and is read when loading.

- {gh-pr}`387` Stop reformatting arrays in json output.

- {gh-pr}`385` {gh-issue}`344` Add sides accessors to branches.

  - `Transformer.side_hv` and `Transformer.side_lv` return the high-voltage and low-voltage sides of a transformer.
  - `Line.side1` and `Line.side2` return the two sides of a line.
  - `Switch.side1` and `Switch.side2` return the two sides of a switch.

  A side is a bus connectable element and has all common attributes of bus connectables. For example,
  `Transformer.side_hv` has the attributes `bus`, `phases`, `res_currents`, `res_powers`, `res_voltages`, etc.

  Passing a branch element and a separate side argument to `rlf.GroundConnection`, `rlf.plotting.plot_voltage_phasors`
  and `rlf.plotting.plot_symmetrical_voltages` is deprecated in favor of passing a branch side directly. For example,
  replace `rlf.GroundConnection(ground=ground, element=transformer, side="HV")` by
  `rlf.GroundConnection(ground=ground, element=transformer.side_hv)`.

- {gh-pr}`382` Improve load flow convergence for networks with step-up transformers by improving the initial guesses for
  the voltages of the buses.

- {gh-pr}`380` {gh-issue}`379` Fix error when neutral ampacity is not passed to `LineParameters.from_geometry`.

- {gh-pr}`374` Rename the `from_dgs` method of `rlf.ElectricalNetwork` to `from_dgs_file` and add a new `from_dgs_dict`
  method to load a network from a DGS-formatted dictionary. The old method is deprecated and will be removed in a future
  release. The `from_dgs_file` method accepts an optional `encoding` parameter to specify the encoding of the DGS file.

- {gh-pr}`371` Deprecate `Transformer.res_voltage_hv` and `Transformer.res_voltage_lv` properties added in the last
  release by mistake. A simpler interface will be added later as described in {gh-issue}`344`.

- {gh-pr}`369` Add `Line.res_ground_potential` property to get the potential of the ground port of lines with shunt
  components. Update JSON file format to version 5 to store this information. Files created with previous versions of
  Roseau Load Flow will still be readable and will warn on loading.

- {gh-pr}`366` Add nominal frequency (`fn`), cooling class (`cooling`) and insulation type (`insulation`) to the
  `TransformerParameters` class. The transformers catalogue has been updated accordingly. The manufacturer names in the
  catalogue have been expanded to better accommodate new transformers (`SE` -> `Schneider Electric`, `FT` ->
  `France Transfo`, ...). More HV/MV transformers have been added to the catalogue. The cooling and insulation are
  described in the new enumeration types `TransformerCooling` and `TransformerInsulation` respectively.

- {gh-pr}`365` Fix minor inconsistency in the calculation of short-circuit parameters of transformers with no open and
  short circuit tests data. The iron losses are now consistently ignored during the calculation of the short-circuit
  parameters.

- {gh-pr}`364` {gh-issue}`363` Fix missing floating neutral of three-phase transformers when the bus does not have a
  neutral.

- {gh-pr}`361` {gh-issue}`300` Raise an error when duplicate line or transformer parameters IDs are used in the same
  network.

- {gh-pr}`362` {gh-issue}`338` Require Python 3.11 or newer.

- {gh-pr}`360` {gh-issue}`359` Fix a bug related to adding short circuits to a bus when the ground fault was not already
  part of the electrical network.

- {gh-pr}`358` Fix a division by zero error during DGS export.

- {gh-pr}`357` Improve support for unbalance calculations.

  - The `res_voltage_unbalance` method now accepts a `definition` parameter to choose between the definitions of the
    voltage unbalance from `'VUF'` (IEC), `'PVUR'` (IEEE) and `'LVUR'` (NEMA).
  - Loads and sources now have a `res_current_unbalance` method to compute the current unbalance.

- {gh-pr}`356` Fix regression since version 0.11.0 where `max_voltage_level` for buses was missing in the catalogue
  networks.

- {gh-pr}`355` {gh-issue}`337` Add HV/MV transformer models to the catalogue.

## Version 0.12.0

```{note}
This is the last version of _Roseau Load Flow_ to support Python 3.10.
```

```{seealso}
This release also includes the modifications that are in the [version 0.12.0-alpha](#version-0120-alpha).
```

### Breaking changes

- The following columns have been renamed in `ElectricalNetwork.transformers_frame`:

  - `bus1_id`, `bus2_id` -> `bus_hv_id`, `bus_lv_id`
  - `phases1`, `phases2` -> `phases_hv`, `phases_lv`

  and the following columns have been renamed in `ElectricalNetwork.res_transformers`:

  - `current1`, `current2` -> `current_hv`, `current_lv`
  - `potential1`, `potential2` -> `potential_hv`, `potential_lv`
  - `voltage1`, `voltage2` -> `voltage_hv`, `voltage_lv`
  - `power1`, `power2` -> `power_hv`, `power_lv`

- The `ElectricalNetwork.crs` now defaults to `None` (no CRS) instead of `"EPSG:4326"`. The attribute is also no longer
  normalized to a `pyproj.CRS` object but is stored as is. Use `CRS(en.crs)` to always get a `pyproj.CRS` object.

### Detailed changes

- A new **experimental** module named `roseau.load_flow_single` has been added for studying balanced three-phase systems
  using the simpler single-line model. This module is unstable and undocumented, use at your own risk.

- Improvements of license validation, particularly during simultaneous use of multiple threads or processes.

- {gh-pr}`351` {gh-issue}`332` Improved support of the network's Coordinate Reference System (CRS).

  - The `CRS` will now default to `None` (no CRS) instead of `"EPSG:4326"` if not provided.
  - The `ElectricalNetwork.crs` attribute is no longer normalized to a `pyproj.CRS` object.
  - The `CRS` can be set when creating a network with the `ElectricalNetwork.from_element` method.
  - The `CRS` is now correctly stored in the JSON file and is read when loading the network.

- {gh-pr}`350` {gh-issue}`349` Fix invalid transformer parameters with no leakage inductance when created from open and
  short circuit tests.

- {gh-pr}`348` The load classes have two new properties: `res_inner_currents` and `res_inner_powers`. These are the
  currents and powers that flow in the inner components of the load as opposed to `res_currents` and `res_powers` that
  flow into the load.

- {gh-pr}`343` {gh-issue}`336` Warn when a line/switch connects buses with different nominal voltages.

- {gh-pr}`341` Compute the transformer's open-circuit (no-load) and short-circuit tests results if they are not
  provided. `TransformerParameters`'s `i0`, `p0`, `vsc`, and `psc` are now always available and no longer return `None`
  when the transformer is created from `z2` and `ym`.

- {gh-pr}`340` Improve the support for the conversion from the PowerFactory DGS format.

  - Add an option to `ElectricalNetwork.from_dgs` to use the element names (`loc_name` in DGS) as IDs. The names must be
    unique for each element type.
  - Read the transformer's maximum loading from the DGS file.
  - Read the bus's nominal voltage from the DGS file.
  - Fix conversion of the transformer's no-load test results.

- {gh-pr}`339` Constant current loads are no longer allowed on a bus with a short-circuit. Previously, the load flow
  would fail with a singular matrix error.

- {gh-pr}`335` Add `GroundConnection` class with the following features:

  - Ground connections for all terminal elements (buses, loads, sources) and all branch elements, (transformers, lines,
    switches). Previously only buses could be connected to ground.
  - Non-ideal (impedant) ground connections with the `impedance` parameter.
  - Access to the current in the ground connection with the `res_current` property.

  The method `Ground.connect` is deprecated in favor of the new class. Replace `ground.connect(bus)` by
  `GroundConnection(ground=ground, element=bus)`. The attribute `Ground.connected_buses` is also deprecated in favor of
  `GroundConnection.connected_elements`.

- {gh-pr}`331` Add `voltage_type` to the `plot_voltage_phasors` function to be able to plot the voltages in
  phase-to-phase or phase-to-neutral. The `plot_symmetrical_voltages` function now plots each sequence in a separate
  axes for better readability.

- {gh-pr}`330` Add phase-to-phase (`res_voltages_pp`) and phase-to-neutral (`res_voltages_pn`) voltage results for
  terminal elements. Voltage unbalance results are now available for all terminal elements with the
  `res_voltage_unbalance` method.

- {gh-pr}`328` Support floating neutrals for transformers. The `Transformer` class constructor now accepts optional
  `connect_neutral_hv` and `connect_neutral_lv` parameters to specify if the neutral is to be connected to the bus's
  neutral or to be left floating. By default the neutral is connected when the bus has a neutral and left floating
  otherwise.

- {gh-pr}`328` The `plot_voltage_phasors` function and the `plot_symmetrical_voltages` functions now also support
  transformers, lines and switches.

- {gh-pr}`325` Rename `Bus.potentials` to `Bus.initial_potentials`. The old attribute and constructor parameter are
  deprecated and will be removed in a future release.

- {gh-pr}`319` {gh-pr}`320` {gh-pr}`321` {gh-issue}`191` Deprecate the notion of "primary" and "secondary" sides of
  transformers in favor of "high-voltage" and "low-voltage" sides following the IEC 60076-1 standard. The following
  parameters of `rlf.Transformer` are deprecated and renamed:

  - `bus1`, `bus2` -> `bus_hv`, `bus_lv`
  - `phases1`, `phases2` -> `phases_hv`, `phases_lv`

  The attributes `bus1`, `bus2`, `phases1`, `phases2`, `winding1`, `winding2`, `phase_displacement` are still available.
  They are aliases to newly added attributes `bus_hv`, `bus_lv`, `phases_hv`, `phases_lv`, `whv`, `wlv`, and `clock`
  respectively. The old attributes will NOT be removed.

  The corresponding columns in `ElectricalNetwork.transformers_frame` and `ElectricalNetwork.res_transformers` have been
  renamed as well. The old columns have been removed.

- {gh-pr}`318` Implement all common and additional three-phase transformer vector groups. Notable addition is
  transformers with clock number 1, common in North America.

## Version 0.12.0-alpha

- Some improvements of the underlying engine:
  - Simplify the center-tapped transformer model in order to improve the convergence speed (especially in case of a
    short-circuit).
  - Add the backward-forward algorithm for the single-phase transformers.
  - Improve the error message if a singular matrix is detected.
  - Build the engine using the `manylinux_2_34` image for Linux distributions (previously it was `manylinux_2_28`).
- {gh-pr}`311` Add French aliases to line enumeration types.
- {gh-pr}`311` Fix `TypeError`s in the `LineParameters.from_coiffier_model`. The error message of invalid models now
  indicates whether the line type or the conductor material is invalid.
- {gh-pr}`310` {gh-issue}`308` Support star and zig-zag windings with non-brought out neutral. In earlier versions,
  vector groups like "Yd11" were considered identical to "YNd11".
- {gh-pr}`307` {gh-issue}`296` Make `line.res_violated` and `bus.res_violated` return a boolean array indicating if the
  corresponding phase is violated. This is consistent with the dataframe results `en.res_lines` and
  `en.res_buses_voltages`. For old behavior, use `line_or_bus.res_violated.any()`.
- {gh-pr}`305` Add missing `tap` column to `en.transformers_frame`.
- {gh-pr}`305` Add `element_type` column to `en.potential_refs_frame` to indicate if the potential reference is
  connected to a bus or a ground.
- {gh-pr}`305` Add missing information to `results_to_dict` with `full=True`. This adds `loading` to lines and
  transformers, `voltage_levels` to buses, and `voltages` to loads and sources.
- {gh-pr}`305` Improve the performance of `res_violated` of buses, lines and transformers.
- {gh-pr}`304` Add top-level modules `rlf.constants` and `rlf.types`. The old modules in the `utils` package are
  deprecated and will be removed in a future release. The `utils` package is for internal use only and should not be
  considered stable.
- {gh-pr}`304` Add top-level module `rlf.sym` for symmetrical components utilities. The `sym_to_phasor`, `phasor_to_sym`
  and `series_phasor_to_sym` functions are moved from the `rlf.converters` module to this module. The old functions are
  deprecated and will be removed in a future release.
- {gh-pr}`303` Fix missing `voltage_level` in `en.res_buses_voltages` when the buses define nominal voltage but not
  voltage limits.
- {gh-pr}`303` Add `rlf.SQRT3` constant for the square root of 3. It can be useful for the conversion between
  phase-to-phase and phase-to-neutral voltages.
- {gh-pr}`303` Improve the performance of some dataframe properties.
- {gh-pr}`301` {gh-issue}`299` Improve the error message when the Jacobian matrix contains infinite or NaN values.

## Version 0.11.0

This release adds official support for Python 3.13 and adds a new experimental backward-forward solver.

### Breaking changes

- The `min_voltage` and `max_voltage` of `Bus` have been replaced by `nominal_voltage` (phase-to-phase, in V), a
  `min_voltage_level` (unitless) and a `max_voltage_level` (unitless).
- The `type` parameter of `TransformerParameters` constructors becomes `vg` for vector group. Replace `type="single"` by
  `vg="Ii0"` and `type="center"` by `vg="Iii0"`.
- The `type` attribute of `TransformerParameters` now returns `three-phase`, `single-phase` or `center-tapped`. Use
  `TransformerParameters.vg` to get the vector group.
- The names of the transformers in the catalogue have been modified to add voltage levels and vector groups. Use
  `rlf.TransformerParameters.get_catalogue()` to see the updated catalogue.
- The `max_current`, `section`, `insulator_type` and `conductor_type` parameters of the `LineParameters` class are
  renamed to `ampacities`, `sections`, `insulators` and `materials` respectively. The new parameters accept arrays of
  values, one per conductor.
- The enumeration `InsulatorType.UNKNOWN` is removed. Please use `None` if the insulator is unknown.
- The definition of constant-current loads is modified to be the magnitudes of the currents and their phase shift from
  the voltages instead of the absolute phase shift. Currents should no longer be rotated by 120° to be in sync with the
  voltages.

### Deprecations

- The enumerated classes `InsulatorType` and `ConductorType` are renamed to `Insulator` and `Material` respectively.
  Their old names are deprecated and will be removed in a future release.
- The deprecated method `LineParameters.from_name_mv` is removed.

### Detailed changes

- {gh-pr}`293` Fixed `loading` calculation for lines and transformers
- {gh-pr}`291` Fixed several bugs in JSON serialization and deserialization.
- {gh-pr}`289` {gh-issue}`264` Improve the `TransformerParameters` class and the transformers catalogue
  - Add 15kV transformers to the catalogue (SE and FT)
  - Add single-phase transformers to the catalogue (Schneider Imprego)
  - Add step-up transformers to the catalogue (Cahors "Série Jaune")
  - Use the correct LV side no-load voltage as defined in the datasheets (some 400V became 410V)
  - Revert {gh-pr}`282` to keep the IEC 600076 names `uhv` and `ulv` for the transformer voltages.
  - Replace the `type` parameter of `TransformerParameters` constructors by `vg` for vector group.
  - `TransformerParameters.type` now returns `three-phase`, `single-phase` or `center-tapped`. Use
    `TransformerParameters.vg` to get vector group.
  - Modify the names of the transformers in the catalogue to add voltage levels and vector groups
- {gh-pr}`285` {gh-issue}`279` Add maximum loading for lines and transformers.
  - The constructors of `Transformer` and `Line` now accept a unitless `max_loading` parameter equal to 1 (=100%) by
    default.
  - The parameter `max_currents` of `LineParameters` is now called `ampacities`.
  - The `Line` class gained a new property `max_currents` that returns the maximal admissible currents (in Amps) for
    each conductor: `line.max_current = line.parameters.ampacity * line.max_loading`.
  - The `res_violated` property of `Transformer` and `Line` now take into account this `max_loading`.
  - The `Line` and `Transformer` classes have a new `res_loading` property to compute the loading of the element:
    - `line.res_loading = line.res_currents / line.parameters.ampacities`
    - `transformer.res_loading = sum(transformer.res_powers) / transformer.parameters.sn`
- {gh-pr}`286` The deprecated method `LineParameters.from_name_mv` is removed.
- {gh-pr}`283` Several changes related to the `LineParameters`:
  - The `max_current`, `section`, `insulator_type` and `conductor_type` parameters are renamed to `max_currents`,
    `sections`, `insulators` and `materials` respectively. The new parameters accept arrays of values, one per
    conductor.
  - The class method `from_geometry` now accepts several additional arguments related to the neutral
    (`material_neutral`, `insulator_neutral`, `max_current_neutral`)
  - The enumerated classes `InsulatorType` and `ConductorType` are renamed to `Insulator` and `Material`. Their old
    names are deprecated and will be removed in a future release.
  - The insulator `UNKNOWN` is removed. Please use `None` if the insulator is unknown.
  - The insulator `NONE` is added. It must be used to describe conductors without insulator.
  - The catalogue has now several additional columns related to the neutral parameters (resistance, reactance,
    susceptance, material, insulator, maximal current). The `get_catalogue` and the `from_catalogue` methods have been
    changed to accept filter on the columns (`material_neutral`, `insulator_neutral`, `section_neutral`)
- {gh-pr}`281` Add official support for Python 3.13.
- {gh-issue}`278` {gh-pr}`280` Modify the `Bus` voltage limits:
  - The `min_voltage` and `max_voltage` parameters and attributes of `Bus` have been replaced by `nominal_voltage`
    (phase-to-phase, in V), a `min_voltage_level` (unitless) and a `max_voltage_level` (unitless).
  - `Bus` gained a new property `res_voltage_levels` that returns the voltage levels of the bus as a percentage of the
    nominal voltage;
  - The JSON file format also changed to take into account these changes. If a `min_voltage` or `max_voltage` existed in
    a file of a previous version, they are lost when upgrading the file.
- {gh-pr}`277` Fix the definition of constant current loads to be the magnitudes of the currents and their phase shift
  from the voltages instead of the absolute phase shift. Currents should no longer be rotated by 120° to be in sync with
  the voltages.
- {gh-pr}`276` Add a backward-forward solver (experimental).
- {gh-pr}`275` Use [uv](https://docs.astral.sh/uv/) instead of [Rye](https://rye.astral.sh/) as dependency manager.
- {gh-pr}`273` Dynamically calculate the stacklevel of the first frame outside of `roseau.load_flow` for warnings
- {gh-pr}`272` {gh-issue}`271`: Fix segfault when phases of a potential reference are not the same as the bus phases.
- {gh-pr}`270` Use [Rye](https://rye.astral.sh/) instead of [Poetry](https://python-poetry.org/) as dependency manager.
- {gh-pr}`269` Optimize the SVG files of the documentation.
- {gh-pr}`268` Set up ReadTheDoc to automatically compile the documentation.
- {gh-pr}`267` Add a section in the documentation on Google Colab secrets.

## Version 0.10.0

- A wheel for Python 3.13 is available.
- The wheels for Windows are now available. The problem was the same as the one of the
  [issue 28551](https://github.com/matplotlib/matplotlib/issues/28551) of the Matplotlib repository.
- {gh-pr}`237` Improvements of the Sphinx configuration.
- {gh-pr}`262` Raise a proper error when a transformer is defined with null impedance.
- {gh-pr}`259` The cache of the license object was not reset after the activation of a new license key.
- {gh-pr}`258` {gh-pr}`261` {gh-pr}`263` Add basic plotting functionality in the new `roseau.load_flow.plotting` module.
  The `plot_interactive_map` function plots an electrical network on an interactive map using the folium library and the
  `plot_voltage_phasors` function plots the voltage phasors of a bus, load or source in the complex plane. The revamped
  plotting section of the documentation demonstrates the plotting functionalities available in Roseau Load Flow with
  examples.
- {gh-pr}`258` The documentation gained a new "advanced" section with a page on floating neutrals and a page on
  potential references.
- {gh-pr}`257` {gh-issue}`252` Updates to the `LineParameters` class:
  - The method `from_name_lv`, deprecated since version 0.6, has been removed. It can be easily replaced by the
    `from_geometry` method.
  - The method `from_name_mv` is deprecated. A new method `from_coiffier_model` is added with the same functionality and
    more flexibility. The new method computes the ampacity of the line based on Coiffier's model and works with
    different numbers of phases.
- {gh-pr}`256` {gh-issue}`250`:
  - Accept scalar values for the `powers`, `currents`, `impedances` parameters of the load classes.
  - Add `rlf.PositiveSequence`, `rlf.NegativeSequence` and `rlf.ZeroSequence` vectors for easier creation of balanced
    quantities.
- {gh-pr}`255` Update the figures of loads and of voltage sources in the documentation to be compliant with the work of
  {gh-pr}`249`.
- {gh-pr}`254` {gh-issue}`251` Allow passing multiple phases to potential references. The `phase` attribute of the
  `PotentialRef` is replaced by `phases`.
- {gh-pr}`249` {gh-issue}`248` Accept scalar values for the `voltages` parameter of the `VoltageSource` class.
- {gh-pr}`247` Add `connect_neutral` parameter to the loads and sources constructor to specify if the neutral is to be
  connected to the bus's neutral or to be left floating. This allows loads connected to the same bus to have different
  neutral connections. The default behavior remains the same as before where the neutral is connected when the bus has a
  neutral and floating otherwise.
- {gh-pr}`246` Improvements to the `rlf.converters` module:
  - Fix `series_phasor_to_sym` function with series that have different phases per element.
  - Make `calculate_voltages` take array-like potentials.
  - Improve typing of several functions.
- {gh-pr}`245` {gh-issue}`244` Fix the `LineParameters.from_geometry` method to not crash when passed `unknown`
  insulator type or `None`.
- Add `res_voltages` to the `VoltageSource` class for symmetry with the other elements. `res_voltages` is always equal
  to the supplied `voltages` for a voltage source.
- {gh-pr}`243` Fix cross-sectional area of DGS line types created from line elements and special case invalid PwF line
  geographical coordinates table.
- {gh-pr}`240` Add tests for switches imported from DGS and improve warning and error messages.
- {gh-pr}`235` **BREAKING CHANGE**: The constructor of the class `ElectricalNetwork` has changed:
  - it accepts keyword arguments only.
  - it accepts the arguments `lines`, `transformers` and `switches` in replacement of the argument `branches`.
  - As a consequence,
    - the results method `res_branches` has been removed. Please use `res_lines`, `res_transformers` and `res_switches`
      methods instead.
    - the field `branches` does not exist anymore. Please use the fields `lines`, `transformers` and `switches`.
- {gh-pr}`235` Move the `Switch` class into its own file `roseau/load_flow/models/switches.py`.
- {gh-pr}`235` {gh-pr}`239` The JSON file format number is upgraded to the version 2. All the files in version 0 or 1
  can still be read. Please upgrade them manually using the following code:
  ```python
  path = "my_json_file.json"
  ElectricalNetwork.from_json(path).to_json(path)
  ```
- {gh-pr}`235` The method `results_to_dict` now accepts the keyword-only argument `full` which allows the export of all
  the results of an element.
- {gh-pr}`235` Solve a bug concerning the accessors to the flexible powers result of flexible power loads. An unwanted
  error was raised.
- {gh-pr}`235` Replace the occurrences of the `str.find` method by the `str.index` function.
- {gh-pr}`235` The method `to_graph` of the class `ElectricalNetwork` now retrieves a graph with additional data store
  in the edges depending on the edge type: line, transformer or switch.
- {gh-pr}`242` Add optional data to the `TransformerParameters` class: manufacturer, efficiency and range.
- {gh-pr}`242` Fixed a bug in the unit of `q_min` and `q_max` in the constructor of `FlexibleParameter`.
- {gh-pr}`242` Add equality operator for the classes `FlexibleParameter`, `Control` and `Projection`.

## Version 0.9.1

```{note}
The wheels for Windows are temporarily unavailable anymore. If you need them, please post an issue on GitHub.
```

- {gh-pr}`231` Add `LineParameters.from_power_factory` and `TransformerParameters.from_power_factory` methods to easily
  import PowerFactory lines and transformer models into Roseau Load Flow.

- {gh-pr}`230` Improve the algorithm for assigning potential references for DGS networks.

- {gh-pr}`229` Several fixes and improvements to the PowerFactory import:

  - Update the "Export Definition Folder" bundled with _Roseau Load Flow_ as a pfd file;
  - Support lines with missing type ID. This is the case when the `TypLne` objects are inherited from an external
    library in PowerFactory and not included in the project being exported; A `LineParameters` object is automatically
    created for these lines;
  - Support "General Load (`ElmLod`)" elements;
  - Preserve Geometry information on buses and branches;
  - Improve handling of phases of several elements. Previously, phases were hard-coded.
  - Fix the unit of the power of static generators;
  - Fix the re-sizing of the matrices of line types without neutral elements;
  - Fix the total power of "MV Loads (`ElmLodmv`)" to take into account the generation power;
  - Fix all loads to no longer ignore the scale factor of the power;
  - Fix the sign of the reactive power of MV and LV loads
  - Fix the ground connection to the source bus

  And many more...

## Version 0.9.0

- {gh-pr}`227` Sources and loads are now allowed to have floating neutrals. This means that a load/source with
  `phases="abcn"` can now be connected to a bus with `phases="abc"`.
- {gh-pr}`225` The `calculate_voltages` function now accepts and return pint quantities.
- MacOS wheels for roseau-load-flow-engine are now published on PyPI. This means that `pip install roseau-load-flow`
  should now work on macOS.
- Added support for running in Google Colab documents.
- Fixed a bug in license checks caching on Windows.
- Added support for Numpy 2.0.
- {gh-issue}`222` {gh-pr}`223` `from_catalogue()` methods of the electrical network and transformer and line parameters
  now perform "full match" comparison on textual inputs. If you need the old behavior, use regular expression wild cards
  `.*` in the input string.
- {gh-issue}`220` {gh-pr}`221` Add `LineParameters.from_open_dss` and `TransformerParameters.from_open_dss` methods to
  easily import OpenDSS lines and transformer models into Roseau Load Flow. More information is available in the
  documentation of these methods.
- {gh-issue}`210` {gh-pr}`219` Add a parameter to `LineParameters.from_catalogue` to choose the number of phases of the
  created line parameters object.
- {gh-pr}`218` Add `Transformer.res_power_losses` to get the total power losses in a transformer.
- {gh-pr}`217` Add an ID override to `TransformerParameters.from_catalogue` similar to `LineParameters.from_catalogue`.
- {gh-issue}`216` {gh-pr}`217` **BREAKING CHANGE**: Rename the `id` parameter of `TransformerParameters` catalogue
  methods to `name` to be consistent with `LineParameters`. **If you call these methods by keyword arguments**, make
  sure to update your usage of `TransformerParameters.from_catalogue(id="xxx")` to
  `TransformerParameters.from_catalogue(name="xxx")`.
- {gh-pr}`212` **BREAKING CHANGE**: Modify the constructor of `TransformerParameters` to take the `z2` and `ym`
  parameters directly instead of the open and short circuit tests parameters. You can still create an object from these
  tests using the `from_open_and_short_circuit_tests` constructor. This change comes with other changes to
  `TransformerParameters`, notably:
  - The `z2`, `ym`, `k`, and `orientation` are now always available as attributes on the instance
  - The `to_zyk` method is deprecated in favour of the direct attribute access on the instance. This method will be
    removed in a future version
  - The parameters `i0`, `p0`, `psc`, and `vsc` are now optional. They return None for instances created using `z2` and
    `ym` directly
  - The JSON representation of `TransformerParameters` has changed, but it is still compatible with the old
    representation.

## Version 0.8.1

- {gh-issue}`214` Solve a bug in the engine when using delta connected flexible loads.
- {gh-pr}`213` Better detection of poorly connected elements as described in {gh-issue}`209`. It raises a proper error
  message.
- {gh-pr}`211` Several improvements of the documentation:
  - Add Open Graph metadata to the documentation page.
  - Error on the susceptance unit in the tables of the `LineParameters`' catalogue.
  - Replot the networks of the catalogue (add a `H1` title, use the Raleway font, only plot the lines to add their
    parameters id in the tooltip)

## Version 0.8.0

- {gh-pr}`207` Fix a bug in the zig-zag three-phase transformer model that led to incorrect active power flow in the
  transformer. The bug affected the 50 kVA transformers that have the type `Yzn11` in the catalogue.
- {gh-pr}`206` {gh-issue}`187` Un-deprecate `results_to_dict/json` methods and remove deprecated
  `results_from_dict/json` methods.
- {gh-pr}`205` {gh-issue}`200` Fix error when propagating the potentials from a voltage source with fewer phases than
  the bus.
- {gh-pr}`204` {gh-issue}`193` Remove restrictions on geometry types. Allow specifying the CRS of the geometries.
- {gh-pr}`203` {gh-issue}`186` Detect invalid element overrides when connecting a new element with the same ID and type
  of an existing element.
- {gh-pr}`202` {gh-issue}`188` Explicitly prevent instantiation of abstract classes.
- {gh-pr}`201` {gh-issue}`185` Add `type` attribute to the load classes and rename branches `branch_type` attribute to
  `type` for consistency. Please replace `branch.branch_type` by `branch.type` in your code. In addition, loads data
  frames gained two new columns:
  1. `type` indicating the load type: constant-(`power`, `current`, `impedance`);
  2. and `flexible` indicating if the load is flexible.
- {gh-pr}`197` Fix a bug in three-phase transformer models that led to excessive reactive power flow in the transformer.
- {gh-pr}`199` Add Schneider Electric EcoDesign transformers to the catalogue. These are tagged with the _AA0Ak_
  efficiency class. Other internal data have been added to the catalogue for testing purposes.
- {gh-pr}`198` Simplify the storage of the transformer catalogues. This is an internal change that should not have
  effects on user code.
- {gh-pr}`196` {gh-issue}`194` Improve the error message when accessing `res_flexible_powers` on a non-flexible load and
  relax the flexible parameters plotting methods to accept an array-like of voltages.
- {gh-pr}`195` Use `latexindent.pl` to automatically indent LaTeX files in the documentation.
- {gh-pr}`192` Speed up results access by up to 3x using several optimization techniques. This is especially noticeable
  in timeseries simulations and when accessing results of large networks.
- {gh-pr}`184` Improve the documentation to have a better SEO (sitemap, metadata and canonical URLs). The navigation
  menu has also been improved.
- {gh-pr}`183` {gh-issue}`181` Update the networks catalogue to better represent the real networks. LV loads are made
  single-phase, MV sources are connected in delta, and MV buses lost their neutral. Voltage, current, and power limits
  are added to the buses, lines, and transformers. The line parameters IDs are also updated to match the new line
  parameters catalogue.
- {gh-pr}`182` Improve the error message when trying to access results on the network before running the load flow.
- {gh-pr}`189` Allow flexible loads to have a null active theoretical power.

## Version 0.7.0

```{important}
Starting with version 0.7.0, Roseau Load Flow is no longer supplied as a SaaS. The software is now available as
a standalone Python library.
```

- The documentation is moved from GitHub Pages to <https://roseau-load-flow.roseautechnologies.com/>.
- Fix a bug in the engine: it was impossible to change the parameters of center-tapped and single phase transformers.
- {gh-pr}`179` Fix a bug in the propagation of potentials when a center-tapped transformer is used without neutral at
  the primary side.
- {gh-pr}`178` {gh-issue}`176` Merge the `results_to_json`, `results_from_json`, `results_to_dict` and
  `results_from_dict` methods of the `ElectricalNetwork` and `Element`s classes into the methods `to_json`, `from_json`,
  `to_dict` and `from_dict` respectively. The old `results_` methods are **deprecated** and will be removed in a future
  release. The new methods will include the results by default, but you can pass `include_results=False` to exclude
  them.
- {gh-pr}`175` {gh-issue}`174` Fix JSON serialization of network with line parameters created from the catalogue.
- {gh-pr}`173` Remove the conda installation option.
- {gh-pr}`168` {gh-issue}`166` Fix initial potentials' propagation.
- {gh-pr}`167` {gh-issue}`161` Add a catalogue of lines using the IEC standards. You can use the method
  `LineParameters.get_catalogue()` to get a data frame of the available lines and the method
  `LineParameters.from_catalogue()` to create a line from the catalogue. Several line types, conductor material, and
  insulation types have been updated. Physical constants have been updated to match the IEC standards where applicable.
- {gh-pr}`167` The class `LineParameters` now takes optional arguments `line_type`, `conductor_type`, `insulator_type`
  and `section`. These parameters are accessible as properties. They are filled automatically when creating a line from
  the catalogue or from a geometry.
- {gh-pr}`167` Replace all `print_catalogue()` methods by `get_catalogue()` methods that return a data frame instead of
  printing the catalogue to the console.
- {gh-pr}`167` Enumeration classes no longer have a `from_string` method, you can call the enumeration class directly
  with the string value to get the corresponding enumeration member. Case-insensitive behavior is preserved.
- {gh-pr}`167` {gh-issue}`122` Add checks on line height and diameter in the `LineParameters.from_geometry()`
  alternative constructor. This method will try to guess a default conductor and insulation type if none is provided.
- {gh-pr}`163` **BREAKING CHANGE:** roseau-load-flow is no longer a SaaS project. Starting with version 0.7.0, the
  software is distributed as a standalone Python package. You need a license to use it for commercial purposes. See the
  documentation for more details. This comes with a huge performance improvement but requires a breaking change to the
  API:
  - The `ElectricalNetwork.solve_load_flow()` method no longer takes an `auth` argument.
  - To activate the license, you need to call `roseau.load_flow.activate_license("MY LICENSE KEY")` or set the
    environment variable `ROSEAU_LOAD_FLOW_LICENSE_KEY` (preferred) before calling
    `ElectricalNetwork.solve_load_flow()`. More information in the documentation.
  - Several methods on the `FlexibleParameter` class that previously required `auth` are changed. Make sure to follow
    the documentation to update your code.
- {gh-pr}`163` {gh-issue}`158` Fix `ElectricalNetwork.res_transformers` returning an empty dataframe when max_power is
  not set.
- {gh-pr}`163` Several unused exception codes were removed. An `EMPTY_NETWORK` code was added to indicate that a network
  is being created with no elements.
- {gh-pr}`163` Remove the `ElectricalNetwork.res_info` attribute. `ElectricalNetwork.solve_load_flow()` now returns the
  tuple (number of iterations, residual).
- {gh-pr}`163` Remove the `Bus.clear_short_circuits()` and `ElectricalNetwork.clear_short_circuits()` methods. It is
  currently not possible to clear short-circuits from the network.
- {gh-pr}`163` Improve performance of network creation and results access.
- {gh-pr}`163` Attributes `phases` and `bus` are now read-only on all elements.
- {gh-pr}`151` Require Python 3.10 or newer.

## Version 0.6.0

- {gh-pr}`149` {gh-issue}`145` Add custom pint wrapper for better handling of pint arrays.
- {gh-pr}`148` {gh-issue}`122` deprecate `LineParameters.from_name_lv()` in favor of the more generic
  `LineParameters.from_geometry()`. The method will be removed in a future release.
- {gh-pr}`142` {gh-issue}`136` Add `Bus.res_voltage_unbalance()` method to get the Voltage Unbalance Factor (VUF) as
  defined by the IEC standard IEC 61000-3-14.
- {gh-pr}`141` {gh-issue}`137` Add `ElectricalNetwork.to_graph()` to get a `networkx.Graph` object representing the
  electrical network for graph theory studies. Install with the `"graph"` extra to get _networkx_. `ElectricalNetwork`
  also gained a new `buses_clusters` property that returns a list of sets of IDs of buses that are connected by a line
  or a switch. This can be useful to isolate parts of the network for localized analysis. For example, to study a LV
  subnetwork of a MV feeder. Alternatively, to get the cluster certain bus belongs to, you can use
  `Bus.get_connected_buses()`.
- {gh-pr}`141` Add official support for Python 3.12. This is the last release to support Python 3.9.
- {gh-pr}`138` Add network constraints for analysis of the results.
  - Buses can define minimum and maximum voltages. Use `bus.res_violated` to see if the bus has over- or under-voltage.
  - Lines can define a maximum current. Use `line.res_violated` to see if the loading of any of the line's cables is too
    high.
  - Transformers can define a maximum power. Use `transformer.res_violated` to see if the transformer loading is too
    high.
  - The new fields also appear in the data frames of the network.
- {gh-pr}`133` {gh-issue}`126` Add Qmin and Qmax limits of flexible parameters.
- {gh-pr}`132` {gh-issue}`101` Document extra utilities including converters and constants.
- {gh-pr}`131` {gh-issue}`127` Improve the documentation of the flexible loads.
  - Add the method `compute_powers` method to the `FlexibleParameter` class to compute the resulting flexible powers for
    a given theoretical power and a list of voltage norms.
  - Add the `plot_control_p`, `plot_control_q` and `plot_pq` methods to the `FlexibleParameter` class to plot the
    control curves and control trajectories.
  - Add the extra `plot` to install `matplotlib` alongside `roseau-load-flow`.
- {gh-pr}`131` Correction of a bug in the error message of the powers setter method.
- {gh-pr}`130` Mark some internal attributes as private, they were previously marked as public.
- {gh-pr}`128` Add the properties `z_line`, `y_shunt` and `with_shunt` to the `Line` class.
- {gh-pr}`125` Speed-up build of conda workflow using mamba.

## Version 0.5.0

- {gh-pr}`121` {gh-issue}`68` Improvements of the `LineParameters` constructor:
  - Delete the `LineModel` class
  - Simplify the `from_dict` method
  - Rename and refactor the method `from_lv_exact` into `from_geometry`.
  - Add documentation for the `LineParameters` alternative constructors.
  - Rename `InsulationType` into `InsulatorType`.
  - Allow the letter "U" for "Underground" line type (only "S" for "Souterrain" in French was accepted). The same with
    the letter "O" for "Overhead" line type (only "A" for "Aérien" in French was accepted).
  - Remove the field `"model"` from the JSON serialization of `LineParameters`.
- {gh-pr}`120` Fix phases of flexible power results.
- {gh-pr}`119` Add explicit error message for singular jacobian.
- {gh-pr}`118` {gh-issue}`95`
  - Add a catalogue of three-phase MV/LV distribution transformers.
  - Remove the class method `TransformerParameters.from_name`.
- {gh-pr}`117` Add prettier to pre-commit
- {gh-pr}`116`
  - Add a catalogue of networks.
  - Add a plotting page to the documentation.
- {gh-pr}`115`
  - Reformat the tutorials in the documentation.
  - Split the "Advanced" tutorial in several smaller files.
  - Remove the Docker installation option.
- {gh-pr}`114` Use Pint >=0.21 to have the percent unit.
- {gh-pr}`113` Raise an error when accessing the results of disconnected elements.
- {gh-pr}`112` Make the geometry serialization optional.
- {gh-pr}`106` Improvements for non-euclidean projections.
- {gh-pr}`104` Remove `roseau.load_flow.utils.BranchType`.
- {gh-issue}`99` Add `Line.res_series_currents` and `Line.res_shunt_currents` properties to get the currents in the
  series and shunt components of lines. Also added `ElectricalNetwork.res_lines` that contains the series losses and
  currents of all the lines in the network. The property `ElectricalNetwork.res_lines_losses` was removed.
- {gh-issue}`100` Fix the `Yz` transformers.
- {gh-pr}`97` Add the model section to the documentation.
- {gh-pr}`96`
  - Add single-phase transformer.
  - Add center-tapped transformer.
  - Remove the `roseau.load_flow.utils.TransformerType` enumeration.
- {gh-pr}`93` Add short-circuit computation.
- {gh-pr}`92`
  - Add the changelog in the documentation.
  - Use Node.js 20 in the Dockerfile.
  - Correction of a dead link in the README.

## Version 0.4.0

- {gh-pr}`91` Rename `resolution_method` into `solver`.
- {gh-issue}`73` {gh-pr}`85` Rename `precision` into `tolerance` and `final_precision` into `residual`.
- {gh-pr}`82` Add the `"newton_goldstein"` solver.
- {gh-pr}`88` Increase the default `alpha` values for flexible parameters.

## Version 0.3.0

- Every network elements have an `id` which must be unique among the same type of elements.
- The argument `n` (number of ports) have been replaced by a `phase(s)` argument which can be for instance `an`, `abc`,
  `abcn`, `ca`, etc.
- The classes `SimplifiedLine` and `ShuntLine` have been merged into a single class `Line` whose behaviour depends on
  the provided `LineParameters`.
- The classes `DeltaDeltaTransformer`, `DeltaWyeTransformer`, `DeltaZigzagTransformer`, `WyeDeltaTransformer`,
  `WyeWyeTransformer` and `WyeZigzagTransformer` have been replaced by an unique `Transformer` class whose behaviour
  depends on the provided `TransformerParameter`.
- The classes `LineCharacteristics` and `TransformerCharacteristics` have been renamed into `LineParameters` and
  `TransformerParameters`.
- The classes `AdmittanceLoad` and `DeltaAdmittanceLoad` have been removed. Please use `ImpedanceLoad` instead, with the
  desired `phases` argument.
- The classes `DeltaImpedanceLoad` and `DeltaPowerLoad` have been removed. Please use the classes `ImpedanceLoad` and
  `PowerLoad` instead with `phases="abc"`.
- The class `FlexibleLoad` have been removed. Please use the new `flexible_params` argument of the `PowerLoad` class
  constructor.
- The `VoltageSource` is not anymore a subclass of the class `Bus`. It can now be connected to a bus just like a load.
- All elements are aware of the network they belong to. It helps the user to avoid mistakes (connecting elements from
  different networks). It also allows showing user warnings when accessing to outdated results.
- All properties retrieving results are now prefixed by `res_`.
- Additional results per elements: `res_potentials`, `res_voltages`, `res_series_losses`, `res_lie_losses`, etc.
- Pandas Data frame results: now, every result can be retrieved in Pandas Data frame from the `ElectricalNetwork`
  instance. These methods are also prefixed by `res_`.
- Every physical input can be given as quantities (magnitude and unit) using the `Q_` class.
- Every result (except Pandas data frame) are quantities (magnitude and unit).
- Elements can all be serialized as JSON.
- Results of an `ElectricalNetwork` can be serialized as JSON and read from a JSON file.
- The documentation has been improved.
