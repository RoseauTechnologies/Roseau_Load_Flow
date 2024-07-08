---
myst:
  html_meta:
    "description lang=en": |
      Release history of Roseau Load Flow - Three-phase unbalanced load flow solver in a Python API by Roseau
      Technologies.
    "description lang=fr": |
      Historique des versions de Roseau Load Flow - Solveur d'écoulement de charge triphasé et déséquilibré dans une
      API Python par Roseau Technologies.
    "keywords lang=fr": version, solveur, simulation, réseau, électrique, bus
    "keywords lang=en": changelog, solver, simulation, distribution grid, bus, model
og:image: https://www.roseautechnologies.com/wp-content/uploads/2024/04/DSCF0091-scaled.webp
og:image:alt: An engineer uses Roseau Load Flow to perform unbalanced electric calculation
og:title: Roseau Load Flow - Unbalanced and multiphase load flow solver
og:description: See what's new in the latest release of Roseau Load Flow !
---

# Changelog

## Unreleased

- {gh-pr}`235` **BREAKING CHANGE**: Several improvements of the JSON file format and of the serialization methods.
  - Move the `Switch` class into its own file `roseau/load_flow/models/switches.py`.
  - The JSON file format number is upgraded to the version 2. In this version:
    - The `"branches"` key is replaced by the keys `"lines"`, `"transformers"` and `"switches"` to split the different
      types of branches.
    - The key `"type"` in each branch is not necessary anymore and is then removed.
    - The keys `"phases1"` and `"phases2"` are removed in favour of the key `"phases"` for the lines and switches.
    - The key `"powers"` in the results part of a flexible power load is renamed `"flexible_powers"` to avoid confusion.
    - The constructor of an `ElectricalNetwork` now takes the arguments `lines`, `transformers` and `switches` instead
      of the parameters `branches`.
    - The accessor `res_branches` is removed from the class `ElectricalNetwork`. Please use `res_lines`,
      `res_transformers` or `res_switches`.
    - A key `"is_multiphase"` has also been added in the JSON file format for a future single-phase format.
  - A bug concerning the accessors to the flexible powers result of flexible power loads has also been solved.

## Version 0.9.1

```{note}
The wheels for Windows are temporarily unavailable anymore. If you need them, please post an issue on GitHub.
```

- {gh-pr}`231` Add `LineParameters.from_power_factory` and `TransformerParameters.from_power_factory`
  methods to easily import PowerFactory lines and transformer models into Roseau Load Flow.
- {gh-pr}`230` Improve the algorithm for assigning potential references for DGS networks.
- {gh-pr}`229` Several fixes and improvements to the PowerFactory import:

  - Update the "Export Definition Folder" bundled with _Roseau Load Flow_ as a pfd file;
  - Support lines with missing type ID. This is the case when the `TypLne` objects are inherited
    from an external library in PowerFactory and not included in the project being exported; A
    `LineParameters` object is automatically created for these lines;
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

- {gh-pr}`227` Sources and loads are now allowed to have floating neutrals. This means that a load/source
  with `phases="abcn"` can now be connected to a bus with `phases="abc"`.
- {gh-pr}`225` The `calculate_voltages` function now accepts and return pint quantities.
- MacOS wheels for roseau-load-flow-engine are now published on PyPI. This means that `pip install roseau-load-flow`
  should now work on macOS.
- Added support for running in Google Colab documents.
- Fixed a bug in license checks caching on Windows.
- Added support for Numpy 2.0.
- {gh-issue}`222` {gh-pr}`223` `from_catalogue()` methods of the electrical network and transformer
  and line parameters now perform "full match" comparison on textual inputs. If you need the old
  behavior, use regular expression wild cards `.*` in the input string.
- {gh-issue}`220` {gh-pr}`221` Add `LineParameters.from_open_dss` and `TransformerParameters.from_open_dss` methods to
  easily import OpenDSS lines and transformer models into Roseau Load Flow. More information is
  available in the documentation of these methods.
- {gh-issue}`210` {gh-pr}`219` Add a parameter to `LineParameters.from_catalogue` to choose the number
  of phases of the created line parameters object.
- {gh-pr}`218` Add `Transformer.res_power_losses` to get the total power losses in a transformer.
- {gh-pr}`217` Add an ID override to `TransformerParameters.from_catalogue` similar to
  `LineParameters.from_catalogue`.
- {gh-issue}`216` {gh-pr}`217` **BREAKING CHANGE**: Rename the `id` parameter of `TransformerParameters`
  catalogue methods to `name` to be consistent with `LineParameters`.
  **If you call these methods by keyword arguments**, make sure to update your usage of
  `TransformerParameters.from_catalogue(id="xxx")` to `TransformerParameters.from_catalogue(name="xxx")`.
- {gh-pr}`212` **BREAKING CHANGE**: Modify the constructor of `TransformerParameters` to take the `z2`
  and `ym` parameters directly instead of the open and short circuit tests parameters. You can still
  create an object from these tests using the `from_open_and_short_circuit_tests` constructor. This
  change comes with other changes to `TransformerParameters`, notably:
  - The `z2`, `ym`, `k`, and `orientation` are now always available as attributes on the instance
  - The `to_zyk` method is deprecated in favour of the direct attribute access on the instance. This
    method will be removed in a future version
  - The parameters `i0`, `p0`, `psc`, and `vsc` are now optional. They return None for instances
    created using `z2` and `ym` directly
  - The JSON representation of `TransformerParameters` has changed, but it is still compatible with
    the old representation.

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
- {gh-pr}`205` {gh-issue}`200` Fix error when propagating the potentials from a voltage source with fewer phases
  than the bus.
- {gh-pr}`204` {gh-issue}`193` Remove restrictions on geometry types. Allow specifying the CRS of the geometries.
- {gh-pr}`203` {gh-issue}`186` Detect invalid element overrides when connecting a new element with the
  same ID and type of an existing element.
- {gh-pr}`202` {gh-issue}`188` Explicitly prevent instantiation of abstract classes.
- {gh-pr}`201` {gh-issue}`185` Add `type` attribute to the load classes and rename branches `branch_type`
  attribute to `type` for consistency. Please replace `branch.branch_type` by `branch.type` in your code.
  In addition, loads data frames gained two new columns:
  1. `type` indicating the load type: constant-(`power`, `current`, `impedance`);
  2. and `flexible` indicating if the load is flexible.
- {gh-pr}`197` Fix a bug in three-phase transformer models that led to excessive reactive power flow in the transformer.
- {gh-pr}`199` Add Schneider Electric EcoDesign transformers to the catalogue. These are tagged with the _AA0Ak_
  efficiency class. Other internal data have been added to the catalogue for testing purposes.
- {gh-pr}`198` Simplify the storage of the transformer catalogues. This is an internal change that should not have
  effects on user code.
- {gh-pr}`196` {gh-issue}`194` Improve the error message when accessing `res_flexible_powers` on a non-flexible load
  and relax the flexible parameters plotting methods to accept an array-like of voltages.
- {gh-pr}`195` Use `latexindent.pl` to automatically indent LaTeX files in the documentation.
- {gh-pr}`192` Speed up results access by up to 3x using several optimization techniques. This is especially
  noticeable in timeseries simulations and when accessing results of large networks.
- {gh-pr}`184` Improve the documentation to have a better SEO (sitemap, metadata and canonical URLs). The navigation
  menu has also been improved.
- {gh-pr}`183` {gh-issue}`181` Update the networks catalogue to better represent the real networks.
  LV loads are made single-phase, MV sources are connected in delta, and MV buses lost their neutral.
  Voltage, current, and power limits are added to the buses, lines, and transformers.
  The line parameters IDs are also updated to match the new line parameters catalogue.
- {gh-pr}`182` Improve the error message when trying to access results on the network before running the load flow.
- {gh-pr}`189` Allow flexible loads to have a null active theoretical power.

## Version 0.7.0

```{important}
Starting with version 0.7.0, Roseau Load Flow is no longer supplied as a SaaS. The software is now available as
a standalone Python library.
```

- The documentation is moved from GitHub Pages to <https://www.roseau-load-flow.roseautechnologies.com/>.
- Fix a bug in the engine: it was impossible to change the parameters of center-tapped and single phase transformers.
- {gh-pr}`179` Fix a bug in the propagation of potentials when a center-tapped transformer is used without neutral at
  the primary side.
- {gh-pr}`178` {gh-issue}`176` Merge the `results_to_json`, `results_from_json`, `results_to_dict`
  and `results_from_dict` methods of the `ElectricalNetwork` and `Element`s classes into the methods
  `to_json`, `from_json`, `to_dict` and `from_dict` respectively. The old `results_` methods are
  **deprecated** and will be removed in a future release. The new methods will include the results by
  default, but you can pass `include_results=False` to exclude them.
- {gh-pr}`175` {gh-issue}`174` Fix JSON serialization of network with line parameters created from the
  catalogue.
- {gh-pr}`173` Remove the conda installation option.
- {gh-pr}`168` {gh-issue}`166` Fix initial potentials' propagation.
- {gh-pr}`167` {gh-issue}`161` Add a catalogue of lines using the IEC standards. You can use the method
  `LineParameters.get_catalogue()` to get a data frame of the available lines and the method
  `LineParameters.from_catalogue()` to create a line from the catalogue. Several line types, conductor
  material, and insulation types have been updated. Physical constants have been updated to match the
  IEC standards where applicable.
- {gh-pr}`167` The class `LineParameters` now takes optional arguments `line_type`, `conductor_type`,
  `insulator_type` and `section`. These parameters are accessible as properties. They are filled
  automatically when creating a line from the catalogue or from a geometry.
- {gh-pr}`167` Replace all `print_catalogue()` methods by `get_catalogue()` methods that return a
  data frame instead of printing the catalogue to the console.
- {gh-pr}`167` Enumeration classes no longer have a `from_string` method, you can call the enumeration
  class directly with the string value to get the corresponding enumeration member. Case-insensitive
  behavior is preserved.
- {gh-pr}`167` {gh-issue}`122` Add checks on line height and diameter in the `LineParameters.from_geometry()`
  alternative constructor. This method will try to guess a default conductor and insulation type if
  none is provided.
- {gh-pr}`163` **BREAKING CHANGE:** roseau-load-flow is no longer a SaaS project. Starting with version
  0.7.0, the software is distributed as a standalone Python package. You need a license to use it for
  commercial purposes. See the documentation for more details. This comes with a huge performance
  improvement but requires a breaking change to the API:
  - The `ElectricalNetwork.solve_load_flow()` method no longer takes an `auth` argument.
  - To activate the license, you need to call `roseau.load_flow.activate_license("MY LICENSE KEY")`
    or set the environment variable `ROSEAU_LOAD_FLOW_LICENSE_KEY` (preferred) before calling
    `ElectricalNetwork.solve_load_flow()`. More information in the documentation.
  - Several methods on the `FlexibleParameter` class that previously required `auth` are changed. Make
    sure to follow the documentation to update your code.
- {gh-pr}`163` {gh-issue}`158` Fix `ElectricalNetwork.res_transformers` returning an empty dataframe
  when max_power is not set.
- {gh-pr}`163` Several unused exception codes were removed. An `EMPTY_NETWORK` code was added to indicate
  that a network is being created with no elements.
- {gh-pr}`163` Remove the `ElectricalNetwork.res_info` attribute. `ElectricalNetwork.solve_load_flow()` now
  returns the tuple (number of iterations, residual).
- {gh-pr}`163` Remove the `Bus.clear_short_circuits()` and `ElectricalNetwork.clear_short_circuits()`
  methods. It is currently not possible to clear short-circuits from the network.
- {gh-pr}`163` Improve performance of network creation and results access.
- {gh-pr}`163` Attributes `phases` and `bus` are now read-only on all elements.
- {gh-pr}`151` Require Python 3.10 or newer.

## Version 0.6.0

- {gh-pr}`149` {gh-issue}`145` Add custom pint wrapper for better handling of pint arrays.
- {gh-pr}`148` {gh-issue}`122` deprecate `LineParameters.from_name_lv()` in favor of the more generic
  `LineParameters.from_geometry()`. The method will be removed in a future release.
- {gh-pr}`142` {gh-issue}`136` Add `Bus.res_voltage_unbalance()` method to get the Voltage Unbalance
  Factor (VUF) as defined by the IEC standard IEC 61000-3-14.
- {gh-pr}`141` {gh-issue}`137` Add `ElectricalNetwork.to_graph()` to get a `networkx.Graph` object
  representing the electrical network for graph theory studies. Install with the `"graph"` extra to
  get _networkx_.
  `ElectricalNetwork` also gained a new `buses_clusters` property that returns a list of sets of
  IDs of buses that are connected by a line or a switch. This can be useful to isolate parts of the
  network for localized analysis. For example, to study a LV subnetwork of a MV feeder. Alternatively,
  to get the cluster certain bus belongs to, you can use `Bus.get_connected_buses()`.
- {gh-pr}`141` Add official support for Python 3.12. This is the last release to support Python 3.9.
- {gh-pr}`138` Add network constraints for analysis of the results.
  - Buses can define minimum and maximum voltages. Use `bus.res_violated` to see if the bus has
    over- or under-voltage.
  - Lines can define a maximum current. Use `line.res_violated` to see if the loading of any of the
    line's cables is too high.
  - Transformers can define a maximum power. Use `transformer.res_violated` to see if the transformer
    loading is too high.
  - The new fields also appear in the data frames of the network.
- {gh-pr}`133` {gh-issue}`126` Add Qmin and Qmax limits of flexible parameters.
- {gh-pr}`132` {gh-issue}`101` Document extra utilities including converters and constants.
- {gh-pr}`131` {gh-issue}`127` Improve the documentation of the flexible loads.
  - Add the method `compute_powers` method to the `FlexibleParameter` class to compute the resulting flexible powers
    for a given theoretical power and a list of voltage norms.
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
  - Allow the letter "U" for "Underground" line type (only "S" for "Souterrain" in French was accepted). The same
    with the letter "O" for "Overhead" line type (only "A" for "Aérien" in French was accepted).
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
- {gh-pr}`113` Raise an error when accessing the results of
  disconnected elements.
- {gh-pr}`112` Make the geometry serialization optional.
- {gh-pr}`106` Improvements for non-euclidean projections.
- {gh-pr}`104` Remove `roseau.load_flow.utils.BranchType`.
- {gh-issue}`99` Add `Line.res_series_currents`
  and `Line.res_shunt_currents` properties to get the currents in the series and shunt components
  of lines. Also added `ElectricalNetwork.res_lines` that contains the series losses and currents
  of all the lines in the network. The property `ElectricalNetwork.res_lines_losses` was removed.
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
- The argument `n` (number of ports) have been replaced by a `phase(s)` argument which can be for
  instance `an`, `abc`, `abcn`, `ca`, etc.
- The classes `SimplifiedLine` and `ShuntLine` have been merged into a single class `Line` whose
  behaviour depends on the provided `LineParameters`.
- The classes `DeltaDeltaTransformer`, `DeltaWyeTransformer`, `DeltaZigzagTransformer`,
  `WyeDeltaTransformer`, `WyeWyeTransformer` and `WyeZigzagTransformer` have been replaced by an
  unique `Transformer` class whose behaviour depends on the provided `TransformerParameter`.
- The classes `LineCharacteristics` and `TransformerCharacteristics` have been renamed into
  `LineParameters` and `TransformerParameters`.
- The classes `AdmittanceLoad` and `DeltaAdmittanceLoad` have been removed. Please use
  `ImpedanceLoad` instead, with the desired `phases` argument.
- The classes `DeltaImpedanceLoad` and `DeltaPowerLoad` have been removed. Please use the classes
  `ImpedanceLoad` and `PowerLoad` instead with `phases="abc"`.
- The class `FlexibleLoad` have been removed. Please use the new `flexible_params` argument of the
  `PowerLoad` class constructor.
- The `VoltageSource` is not anymore a subclass of the class `Bus`. It can now be connected to a bus
  just like a load.
- All elements are aware of the network they belong to. It helps the user to avoid mistakes
  (connecting elements from different networks). It also allows showing user warnings when accessing
  to outdated results.
- All properties retrieving results are now prefixed by `res_`.
- Additional results per elements: `res_potentials`, `res_voltages`, `res_series_losses`,
  `res_lie_losses`, etc.
- Pandas Data frame results: now, every result can be retrieved in Pandas Data frame from the
  `ElectricalNetwork` instance. These methods are also prefixed by `res_`.
- Every physical input can be given as quantities (magnitude and unit) using the `Q_` class.
- Every result (except Pandas data frame) are quantities (magnitude and unit).
- Elements can all be serialized as JSON.
- Results of an `ElectricalNetwork` can be serialized as JSON and read from a JSON file.
- The documentation has been improved.

<!-- Local Variables: -->
<!-- mode: gfm -->
<!-- fill-column: 120 -->
<!-- coding: utf-8 -->
<!-- ispell-local-dictionary: "british" -->
<!-- End: -->
