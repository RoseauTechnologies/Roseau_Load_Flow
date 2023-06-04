# Changelog

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
