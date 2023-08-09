# Changelog

## Version 0.5.0

**In development**

* [PR114](https://github.com/RoseauTechnologies/Roseau_Load_Flow/pull/114) Use Pint >=0.21 to have the percent unit.
* [PR113](https://github.com/RoseauTechnologies/Roseau_Load_Flow/pull/113) Raise an error when accessing the results of
  disconnected elements.
* [PR112](https://github.com/RoseauTechnologies/Roseau_Load_Flow/pull/112) Make the geometry serialization optional.
* [PR106](https://github.com/RoseauTechnologies/Roseau_Load_Flow/pull/106) Improvements for non-euclidean projections.
* [PR104](https://github.com/RoseauTechnologies/Roseau_Load_Flow/pull/104) Remove `roseau.load_flow.utils.BranchType`
* [GH99](https://github.com/RoseauTechnologies/Roseau_Load_Flow/issues/99) Add `Line.res_series_currents`
  and `Line.res_shunt_currents` properties to get the currents in the series and shunt components
  of lines. Also added `ElectricalNetwork.res_lines` that contains the series losses and currents
  of all the lines in the network. The property `ElectricalNetwork.res_lines_losses` was removed.
* [GH100](https://github.com/RoseauTechnologies/Roseau_Load_Flow/issues/100) Fix the `Yz` transformers
* [PR97](https://github.com/RoseauTechnologies/Roseau_Load_Flow/pull/97) Add the model section to the documentation
* [PR96](https://github.com/RoseauTechnologies/Roseau_Load_Flow/pull/96)
    * Add single-phase transformer
    * Add center-tapped transformer
    * Remove the `TransformerType` enumeration
* [PR93](https://github.com/RoseauTechnologies/Roseau_Load_Flow/pull/93) Add short circuit computation
* [PR92](https://github.com/RoseauTechnologies/Roseau_Load_Flow/pull/92)
    * Add the changelog in the documentation
    * Use NodeJs 20 in the Dockerfile
    * Correction of a dead link in the README

## Version 0.4.0

* [PR91](https://github.com/RoseauTechnologies/Roseau_Load_Flow/pull/91) Rename `resolution_method` into `solver`.
* [GH73](https://github.com/RoseauTechnologies/Roseau_Load_Flow/issues/73)
  [PR85](https://github.com/RoseauTechnologies/Roseau_Load_Flow/pull/85) Rename `precision` into `tolerance` and
  `final_precision` into `residual`.
* [PR82](https://github.com/RoseauTechnologies/Roseau_Load_Flow/pull/82) Add the `"newton_goldstein"` solver.
* [PR88](https://github.com/RoseauTechnologies/Roseau_Load_Flow/pull/88) Increase the default `alpha` values for
  flexible parameters.

## Version 0.3.0

* Every network elements have an `id` which must be unique among the same type of elements.
* The argument `n` (number of ports) have been replaced by a `phase(s)` argument which can be for
  instance `an`, `abc`, `abcn`, `ca`, etc.
* The classes `SimplifiedLine` and `ShuntLine` have been merged into a single class `Line` whose
  behaviour depends on the provided `LineParameters`.
* The classes `DeltaDeltaTransformer`, `DeltaWyeTransformer`, `DeltaZigzagTransformer`,
  `WyeDeltaTransformer`, `WyeWyeTransformer` and `WyeZigzagTransformer` have been replaced by an
  unique `Transformer` class whose behaviour depends on the provided `TransformerParameter`.
* The classes `LineCharacteristics` and `TransformerCharacteristics` have been renamed into
  `LineParameters` and `TransformerParameters`.
* The classes `AdmittanceLoad` and `DelatAdmittanceLoad` have been removed. Please use
  `ImpedanceLoad` instead, with the desired `phases` argument.
* The classes `DeltaImpedanceLoad` and `DeltaPowerLoad` have been removed. Please use the classes
  `ImpedanceLoad` and `PowerLoad` instead with `phases="abc"`.
* The class `FlexibleLoad` have been removed. Please use the new `flexible_params` argument of the
  `PowerLoad` class constructor.
* The `VoltageSource` is not any more a subclass of the class `Bus`. It can now be connected to a bus
  just like a load.
* All elements are aware of the network they belong to. It helps the user to avoid mistakes
  (connecting elements from different networks). It also allows showing user warnings when accessing
  to outdated results.
* All properties retrieving results are now prefixed by `res_`.
* Additional results per elements: `res_potentials`, `res_voltages`, `res_series_losses`,
  `res_lie_losses`, etc.
* Pandas Data frame results: now, every result can be retrieved in Pandas Data frame from the
  `ElectricalNetwork` instance. These methods are also prefixed by `res_`.
* Every physical input can be given as quantities (magnitude and unit) using the `Q_` class.
* Every result (except Pandas data frame) are quantities (magnitude and unit).
* Elements can all be serialized as JSON.
* Results of an `ElectricalNetwork` can be serialized as JSON and read from a JSON file.
* The documentation has been improved.

<!-- Local Variables: -->
<!-- mode: gfm -->
<!-- fill-column: 100 -->
<!-- coding: utf-8 -->
<!-- ispell-local-dictionary: "british" -->
<!-- End: -->
