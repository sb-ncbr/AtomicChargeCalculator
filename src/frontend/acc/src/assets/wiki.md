# Atomic Charge Calculator III

Atomic Charge Calculator III (ACC III) is a web application that provides a user interface for computing partial atomic charges. The application consists of five pages: the main introductory page, computation setup, visualisation of the results, listing of uploaded files, and listing of previous calculations.

# Main page

The main page offers a possibility to upload your own structures (in one of the supported formats: SDF, Mol2, PDB, and mmCIF).

Clicking on the **Compute charges** button will automatically select the most appropriate method, execute the computation, and redirect to the Results page.
**Setup computation** can be used for manually selecting the method and parameters. Additionally, there are advanced settings to choose from:
- `Atoms of PDB/mmCIF files` - Which atoms of structures are calculated: `All atoms` (default), `Without water`, which keeps ligands and ions, or `Polymers only`, the protein and nucleic acid chains. Modified residues, such as selenomethionine, belong to their chain and stay.
- `Permissive Types` - Use similar parameters for similar atom/bond types if no exact match is found (enabled by default).

![compute](/help/compute.png)

## Input files notes
The input file size is limited to 50 MB.
- **PDB, mmCIF**: When the file contains multiple models, only the first one is used for computation. When an atom has alternative locations, only the first one is used. Bonds of ligands and modified residues are taken from the file (`CONECT` records of PDB, `_chem_comp_bond` of mmCIF) or, when the file does not have them, from the wwPDB [Chemical Component Dictionary](https://www.wwpdb.org/data/ccd). Atom IDs of the calculated atoms of mmCIF files (`_atom_site.id`) must be positive integers.
- **SDF**: Both MOL V2000 and V3000 are supported.

## How to set input charge values
Formal charges, if present, are read from an input file as well. Their sum is used as a total molecular
charge, which is used by some methods (ABEEM, EEM, EQeq, Eqeq+C, QEq, SFKEEM, SMP/QEq, TSEF).

The specification of input formal charges differs among supported file formats. ACC III reads the following:

- **SDF**: The charge field of the atom lines and `M CHG` lines for MOL V2000; for MOL V3000, the charge is read from `CHG` property of `ATOM` records. Refer to the [documentation](https://www.daylight.com/meetings/mug05/Kappler/ctfile.pdf) for details on the format.

- **PDB**: Columns 79-80 of the [`ATOM`](https://www.wwpdb.org/documentation/file-format-content/format33/sect9.html#ATOM) record.

- **mmCIF**: [`_atom_site.pdbx_formal_charge`](https://mmcif.wwpdb.org/dictionaries/mmcif_pdbx_v50.dic/Items/_atom_site.pdbx_formal_charge.html) record

- **Mol2**: The `charge` attribute of the `@<TRIPOS>UNITY_ATOM_ATTR` records.

PDB and mmCIF files are processed using the [GEMMI](https://gemmi.readthedocs.io/en/latest/) library.

# Protonation

Since ACC III is not limited to a specific class of molecules, it does not automatically protonate input structures. Protonation strongly depends on molecular context and chemical environment, and a reliable general solution is not feasible for arbitrary molecular systems. Therefore, users must provide correctly protonated structures prior to charge calculation. While specialised tools can address protonation for well-defined molecule classes, such assumptions cannot be safely generalised in ACC III. Based on our experience, we recommend protonating the structure using the following tools:

* *Hydride* ([https://hydride.biotite-python.org/](https://hydride.biotite-python.org/)) is a versatile command-line tool that supports all formats compatible with ACC III. Its main limitation is limited support for pH-dependent protonation. Hydride adds pH-dependent hydrogens only to standard amino acids in proteins, and protonation states are determined solely by comparing residue pKa values with the specified pH, without considering the local environment.

* *PDB2PQR* ([https://server.poissonboltzmann.org/](https://server.poissonboltzmann.org/)) is a specialised tool for adding hydrogens to proteins. It is available as both a command-line application and a web server. PDB2PQR supports protonation across a wide pH range and accounts for the local environment when determining protonation states. Its main limitation is that it only supports standard amino acids in proteins.


# Computation settings

Based on the molecules provided (in all files), methods and parameters that are suitable for all structures are displayed. The parameter set is suitable for a given input if it covers all the atomic types contained in the input files. A method is suitable if it has at least one suitable set of parameters or uses no parameters. A method is also omitted if it does not support the input molecules; for example, PEOE requires that the formal charges of every bonded part of a molecule add up to zero. For a file that contains at least one big molecule, i.e., one with over 20,000 atoms, ABEEM, EEM, EQeq, EQeq+C, QEq, SFKEEM, SQE, SQE+q0, and SQE+qp are calculated with a cutoff of 12 Å instead of in full (above 80,000 atoms with cover), and DelRe, DENR, KCM, MGC, SMP/QEq, and TSEF are omitted. The [PDF document](https://acc.biodata.ceitec.cz/methods.pdf) describes cutoff and cover.

Automatic selection works in the same manner. After initial filtering described above, the first suitable method with its first suitable parameter set is used. The order of preference is the same for every input; it starts with SQE+qp and EEM.

![setup](/help/setup.png)

All the methods and parameters have direct links to the original publications. The notes of a method say what to know before using it, such as which molecules it supports. The theoretical background of the methods is summarised in the standalone [PDF document](https://acc.biodata.ceitec.cz/methods.pdf). For easy identification, the name of the parameters used in a publication is enclosed in brackets.

# Results

The final page features the visualisation of the charges and the possibility to download the calculated charges. At the top, it states which method and parameters were used (useful when the automatic selection was used).

To switch between multiple structures or charges, the user can use the select box.

Each method and parameter set is calculated on its own. When a calculation fails for a file, the page lists the charges that are not available with the reason, and shows the others; when all of them fail, the computation fails with the reasons. Charges beyond ±10 e cannot be shown; such a calculation is listed as not available, too.

The page also warns about what [ChargeFW](https://github.com/sb-ncbr/chargefw) found in the input or in the charges: missing hydrogens, atoms of ligands or modified residues without bonds (their bonds are neither in the file nor in the Chemical Component Dictionary), charges that are probably wrong (atoms much closer than bonded atoms are, or charges far from the formal charges), and PQR or Mol2 files that are not in the download.

![results-select](/help/results-select.png)

## Visualisation modes
ACC III features a fast Molstar viewer to visualise calculated charges. There are three standard modes the user can select – Balls and sticks, Cartoon, and Surface – see example (1F16):

<br>

<img src="https://github.com/sb-ncbr/AtomicChargeCalculator/blob/a0dc907ed85d91e2e2eecf0badaa9b33efe3b856/resources/github-images/1F16_bas.png" alt="bas" width="33%" />
<img src="https://github.com/sb-ncbr/AtomicChargeCalculator/blob/a0dc907ed85d91e2e2eecf0badaa9b33efe3b856/resources/github-images/1F16_cartoon.png" alt="cartoon" width="33%" />
<img src="https://github.com/sb-ncbr/AtomicChargeCalculator/blob/e01cfd9d4dda45cbd1d151efb7e66d8c78f35174/resources/github-images/1F16_surface_smooth.png" alt="surface" width="33%" />

<br>
<br>

The default is determined by the structure itself.
Note that to visualise mmCIF files, they must contain `_atom_site` category

## Colouring options
Atoms are coloured by charge by default – red for negative charges and blue for positive ones.

In cartoon mode, the colour of individual residues is determined according to the sum of the values of charges of all the atoms comprising them. In surface mode, the point on the surface of the molecule is coloured according to the nearest atom. Alternatively, colouring by charges can be disabled – colours are selected based on the elements.

## Downloading data
The charges are available in four formats – plain text, Mol2, PQR, and mmCIF. Plain text and mmCIF are present for all the inputs, PQR for PDB and mmCIF inputs (most likely proteins) and Mol2 for SDF and Mol2 inputs (small molecules). PQR cannot hold chain IDs longer than one character, which large structures have; the PQR file of such a structure is left out of the download.


### ACC III plain-text output format
The plain-text export contains one block per molecule. Each block starts with the molecule name on a separate line, followed by a single line with whitespace-separated partial atomic charges written in the same atom order as in the processed input structure. When a file contains multiple molecules, the blocks are written consecutively.

A simplified example looks as follows:

```text
MOLECULE_1
-0.12345 0.23456 -0.11111
MOLECULE_2
0.33333 -0.22222 0.11111 0.44444
```

### mmCIF output format

ACC III stores charges in custom mmCIF categories. For a complete reference, see the [extension dictionary](https://github.com/sb-ncbr/charges-schema). For PDB and mmCIF inputs, the file is the uploaded structure with the charges added. Atoms of the first model that were not calculated, such as water left out by the settings or other alternative locations, are removed. Other models are kept, without charges.

### PQR output format
The second-to-last column of ATOM and HETATM records in PQR files is used to store partial atomic charges, see the [PQR format specification](https://apbs.readthedocs.io/en/latest/formats/pqr.html).

### Mol2 output format
The ninth column of ATOM records in Mol2 files is used to store partial atomic charges, see the [Mol2 format specification](https://aideepmed.com/DockRMSD/mol2.pdf).

# File management
After logging in, the user can filter, search, delete, and download uploaded files or upload new ones until the quota is reached.
![file-management](https://github.com/user-attachments/assets/47b3ea44-0262-4b59-84d0-8d5c65610d3d)

Additionally, the user can select files and trigger a computation (similar to the process on the [Main page](#main-page)) through a dialogue.
![file-management-compute](https://github.com/user-attachments/assets/eeee9a2a-5c15-4ccf-85c0-603169ae2883)

# Calculation management
The calculation management page allows you to view, download, and delete previous calculations. Calculations are also limited by quota. Hovering over calculation or file badges will show additional information.
![calculation-management](/help/calculation-management.png)

# API

For programmatic access, the ACC III API can be used. Below, we demonstrate a typical ACC III workflow. See the [complete interactive documentation](https://acc.biodata.ceitec.cz/api/docs) for the full OpenAPI description and all request/response schemas.

Successful file uploads return file hashes that are then reused in later requests. Successful calculations have their own computation identifier (UUID), which can be used to poll the calculation state or download the final archive.

## 1. List available methods
Use this endpoint to obtain all charge-calculation methods currently exposed by ACC III. Each method entry contains the public method name, its internal identifier, full name, publication reference, method type (`2D`, `3D`, or `other`), information about whether the method requires a parameter set, and notes about the method, such as the molecules it supports.

```bash
curl -X GET 'https://acc.biodata.ceitec.cz/api/v1/charges/methods/available' \
  -H 'accept: application/json'
```

Response (truncated):
```json
{
  "success": true,
  "data": [
    {
      "name": "SQE+qp",
      "internalName": "sqeqp",
      "fullName": "Split-charge Equilibration with Parameterized Initial Charges",
      "publication": "10.1186/s13321-021-00528-w",
      "type": "3D",
      "hasParameters": true,
      "notes": "The parameterized starting charges are shifted within every bonded part to add up to its formal charge."
    },
    {
      "name": "EEM",
      "internalName": "eem",
      "fullName": "Electronegativity Equalization Method",
      "publication": "10.1021/ja00275a013",
      "type": "3D",
      "hasParameters": true,
      "notes": null
    }
  ]
}
```

If a method uses parameters, they can be queried separately using `GET /api/v1/charges/parameters/{method_name}/available`. The `{method_name}` corresponds `internalName` returned in the previous request.

## 2. Upload input files
The following example uses `curl` to upload multiple files simultaneously by specifying the `-F` option once for each file.

```bash
curl -X POST 'https://acc.biodata.ceitec.cz/api/v1/files/upload' \
  -H 'accept: application/json' \
  -H 'Content-Type: multipart/form-data' \
  -F 'files=@molecule1.sdf' \
  -F 'files=@molecule2.pdb'
```

Example response:
```json
{
  "success": true,
  "data": [
    {
      "file": "molecule1.sdf",
      "fileHash": "<fileHash1>",
      "stats": {
        "totalMolecules": 2,
        "totalAtoms": 27,
        "atomTypeCounts": [
          { "symbol": "C", "count": 12 },
          { "symbol": "H", "count": 13 },
          { "symbol": "O", "count": 2 }
        ]
      }
    },
    {
      "file": "molecule2.pdb",
      "fileHash": "<fileHash2>",
      "stats": {
        "totalMolecules": 1,
        "totalAtoms": 1452,
        "atomTypeCounts": [
          { "symbol": "C", "count": 912 },
          { "symbol": "N", "count": 248 },
          { "symbol": "O", "count": 280 },
          { "symbol": "S", "count": 12 }
        ]
      }
    }
  ]
}
```

Each entry also contains `stats` with the number of molecules and atoms in the file and the count of each element.
## 3. Get suitable methods for uploaded files
Once the files are uploaded, ACC III can filter the method catalogue and return only methods that are suitable for all provided structures. Suitability is evaluated from the uploaded content, read with the `selection` and `permissiveTypes` settings of the calculation. The response contains the list of suitable methods and, for each method, the parameter sets that can be used with the supplied files.

```bash
curl -X POST 'https://acc.biodata.ceitec.cz/api/v1/charges/methods/suitable' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "fileHashes": [
    "<fileHash1>",
    "<fileHash2>"
  ],
  "selection": "all",
  "permissiveTypes": true
}'
```

Response:
```json
{
  "success": true,
  "data": {
    "methods": [
      {
        "name": "SQE+qp",
        "internalName": "sqeqp",
        "fullName": "Split-charge Equilibration with Parameterized Initial Charges",
        "publication": "10.1186/s13321-021-00528-w",
        "type": "3D",
        "hasParameters": true,
        "notes": "The parameterized starting charges are shifted within every bonded part to add up to its formal charge."
      }
    ],
    "parameters": {
      "sqeqp": [
        {
          "fullName": "Schindler 2021 (CCD_gen)",
          "internalName": "SQEqp_Schindler2021_CCD_gen",
          "publication": "10.1186/s13321-021-00528-w",
          "method": "sqeqp",
          "notes": "Parameterized to reproduce B3LYP/6-311G/NPA charges"
        }
      ]
    },
    "warnings": []
  }
}
```

Note that, in web interface, ACC III automatically uses the first suitable method and the first suitable parameter set (if the method has parameters).

## 4. Calculate charges
The calculation of partial atomic charges usually follows. Users provide calculation configurations, file hashes, and optional advanced settings. If `configs` is empty, ACC III automatically selects the most suitable method and parameters.

Each configuration names a method and, if the method has parameters, a parameter set by its `internalName`. A request with an unknown method or parameter set is rejected; list the IDs with `/charges/parameters/<method>/available`. IDs used before the [core migration](#core-migration) are no longer accepted.

```bash
curl -X POST 'https://acc.biodata.ceitec.cz/api/v1/charges/calculate' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "configs": [
    {
      "method": "sqeqp",
      "parameters": "SQEqp_Schindler2021_CCD_gen"
    }
  ],
  "fileHashes": [
    "<fileHash1>",
    "<fileHash2>"
  ],
  "settings": {
    "selection": "all",
    "permissiveTypes": true
  }
}'
```

The `selection` setting chooses the atoms of PDB/mmCIF files: `all` (default), `polymers-and-ligands` (without water), or `polymers` (protein and nucleic acid chains with their modified residues). The former `readHetatm` and `ignoreWater` settings are refused; see [core migration](#core-migration).

Example response:
```json
{
  "success": true,
  "data": {
    "computationId": "<comp_id>",
    "results": [
      {
        "config": {
          "method": "sqeqp",
          "parameters": "SQEqp_Schindler2021_CCD_gen"
        },
        "calculations": [
          {
            "file": "molecule.sdf",
            "fileHash": "<fileHash1>",
            "charges": {
              "TEST": [
                -0.16261638412926122,
                0.12703306647254375,
                0.5926350973399765,
                0.6143192179940414,
                0.03655979848866364,
                0.03655979848866364,
                0.03655979848866364
              ]
            },
            "config": {
              "method": "sqeqp",
              "parameters": "SQEqp_Schindler2021_CCD_gen"
            }
          }
        ]
      }
    ]
  }
}
```

Each method and parameter set is calculated on its own. When the calculation fails for a file, its result lists the file under `failures` with the reason, and the other configurations are not affected. A calculation lists everything [ChargeFW](https://github.com/sb-ncbr/chargefw) warns about under `warnings`: problems of its file, such as atoms without bonds, and of the calculation, such as missing hydrogens or charges that are probably wrong. Each warning has ChargeFW's code in `kind`, such as `unbonded_residue_atoms`, a `message`, its `source` (`import`, `input`, `charge`, `plan`, or `output`), the `molecule` it is about, and the positions of the atoms it names in `atomIndices`. A warning of source `output` names a PQR or MOL2 file that ChargeFW cannot write, such as PQR for chain IDs longer than one character; the charges are calculated, but the file is not in the download. A failure has the `kind` of its reason and every reason ChargeFW gave in `issues`. When no configuration gives charges for any file, the request fails, and its message gives the reasons.

Finally, we can download the charges in a zip format, substituting `<comp_id>`:

```bash
curl -X GET 'https://acc.biodata.ceitec.cz/api/v1/files/download/computation/<comp_id>' \
  -H 'accept: application/zip' \
  -o charges.zip
```
# Core migration

ACC III first calculated charges with [ChargeFW2](https://github.com/sb-ncbr/ChargeFW2). It now uses its successor, [ChargeFW](https://github.com/sb-ncbr/chargefw) 3, a new implementation of the same charge methods. This section summarises what changed for users of ACC III; the other sections describe the current state only. The ChargeFW documentation describes the [differences from ChargeFW2](https://chargefw.readthedocs.io/en/latest/about/chargefw2.html) in detail.

## Charges

For the molecules we compared, most methods give the same charges as before. Charges can still differ, so an earlier calculation is not always reproduced exactly:

- **Reading the input.** Problems in reading bonds and formal charges were fixed, mostly for PDB and mmCIF structures. Methods that use bonds give other charges for the atoms concerned and their surroundings.
- **Methods.** The methods were checked against their publications, and some of them, as well as some parameter values, were corrected.
- **Structures of several parts.** In a structure of several bonded parts, such as a protein with ligands and water, or a salt, SQE+qp now preserves the formal charge of each bonded part separately. Methods that cannot give such molecules correct charges are no longer offered for them.

## Input

- **Atoms of structures.** One selection replaces the `Read HETATM` and `Ignore water` settings (`readHetatm` and `ignoreWater` in the API): all atoms, without water (`polymers-and-ligands`), or polymers only (`polymers`). Polymers keep their modified residues, such as selenomethionine, which were left out with the HETATM records before. Without water, all water residues are left out, not only those named `HOH`.
- **Stored computations** keep their charges. Those made without HETATM records are listed as `Without HETATM records` (`without-hetatm` in the API) and cannot be calculated again.
- **Bonds of ligands and modified residues** are taken from the file first and from the Chemical Component Dictionary otherwise; before, only the dictionary was used.
- **Formal charges** are now read from Mol2 files too.
- **Atom IDs of mmCIF files** have to be positive integers for the calculated atoms, because the download keeps the uploaded structure.

## Methods and parameters

- **Parameter-set IDs** no longer have a two-digit priority: the former `SQEqp_10_Schindler2021_CCD_gen` is now `SQEqp_Schindler2021_CCD_gen`. The exception is `KCM_00_original`, now `KCM_original_initial`. The API refuses the former IDs.
- **Order of parameter sets** is the same for every input; it no longer depends on whether the input contains a protein, so the automatically selected parameters can differ.
- **Large structures.** As before, a cutoff is used above 20,000 atoms. More methods support it now, among them SQE+qp, which can therefore be selected automatically for large structures when its parameters fit the input. Above 80,000 atoms, cover is used; it works differently than before, so the charges of such structures can change.
- **Notes** of methods say what to know before using them.

## Results

- **Each method and parameter set is calculated on its own.** When one fails for a file, the others are shown, and ACC III gives the reason. Before, the whole computation failed.
- **Warnings.** ACC III shows what ChargeFW found in the input and in the charges, such as missing hydrogens, atoms without bonds, and charges that are probably wrong.
- **Charges beyond ±10 e** are reported as not available.
- **Downloads.** The plain-text format is unchanged. The mmCIF download of a structure is based on the uploaded structure, with charges added to the selected atoms of the first model. Mol2 and PQR files differ in details, and a PQR file is not written for a structure with chain IDs longer than one character.
- **Every computation is calculated.** ACC III no longer reuses charges stored from an earlier computation of the same file and settings.

## Speed

Calculations with a cutoff are faster: QEq of 8YAX (40,738 atoms) took 8 s where ChargeFW2 took 26 s, measured with a release candidate of ChargeFW 3. Other calculations were not made faster, and some take longer.

# Limitations

To ensure stable and fair access for all users, the public web API is subject to reasonable usage limits. Users requiring large-scale calculations are encouraged to use [ChargeFW](https://github.com/sb-ncbr/chargefw) locally; see its [documentation](https://chargefw.readthedocs.io/en/latest/).

# Bug reporting

If you encounter an error, please send a report to tomas.racek@muni.cz or open a [GitHub issue](https://github.com/sb-ncbr/AtomicChargeCalculator/issues). Thank you!