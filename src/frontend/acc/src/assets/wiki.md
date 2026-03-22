# Atomic Charge Calculator III

Atomic Charge Calculator III (ACC III) is a web application that provides a user interface for computing partial atomic charges. The application consists of five pages: the main introductory page, computation setup, visualisation of the results, listing of uploaded files, and listing of previous calculations.

# Main page

The main page offers a possibility to upload your own structures (in one of the supported formats: SDF, Mol2, PDB, and mmCIF).

Clicking on the **Compute charges** button will automatically select the most appropriate method, execute the computation and redirect to the Results page. **Setup computation** can be used for manually selecting the method and parameters. Additionally, there are three advanced settings to choose from:
- `Read HETATM` - Read HETATM records from PDB/mmCIF files (enabled by default).
- `Ignore Water` - Discard water molecules from PDB/mmCIF files (disabled by default).
- `Permissive Types` - Use similar parameters for similar atom/bond types if no exact match is found (enabled by default).

![compute](https://github.com/user-attachments/assets/f782d58e-a68a-48e1-a913-1fa5b76ea4c9)

## Input files notes
The input file size is limited to 50 MB.
- **PDB, mmCIF**: When the file contains multiple models, only the first one is used for computation. All
atoms are considered.
- **SDF**: Both MOL V2000 and V3000 are supported.

## How to set input charge values
Formal charges, if present, are read from an input file as well. Their sum is used as a total molecular
charge, which is used by some methods (ABEEM, EEM, EQeq, Eqeq+C, QEq, SFKEEM, SMP/QEq,
TSEF).

The specification of input formal charges differs among supported file formats. ACC II reads the following:

- **SDF**: `M CHG` lines for MOL V2000; for MOL V3000, the charge is read from `CHG` property of `ATOM` records. Refer to the [documentation](https://www.daylight.com/meetings/mug05/Kappler/ctfile.pdf) for details on the format.

- **PDB**: Columns 79-80 of the [`ATOM`](https://www.wwpdb.org/documentation/file-format-content/format33/sect9.html#ATOM) record.

- **mmCIF**: [`_atom_site.pdbx_formal_charge`](https://mmcif.wwpdb.org/dictionaries/mmcif_pdbx_v50.dic/Items/_atom_site.pdbx_formal_charge.html) record; or [`_chem_comp.pdbx_formal_charge`](https://mmcif.wwpdb.org/dictionaries/mmcif_pdbx_v50.dic/Items/_chem_comp.pdbx_formal_charge.html) record in
case of chemical components.

- **Mol2**: Not supported.

PDB and mmCIF files are processed using the [GEMMI](https://gemmi.readthedocs.io/en/latest/) library.

# Protonation

Since ACC III is not limited to a specific class of molecules, it does not automatically protonate input structures. Protonation strongly depends on molecular context and chemical environment, and a reliable general solution is not feasible for arbitrary molecular systems. Therefore, users must provide correctly protonated structures prior to charge calculation. While specialised tools can address protonation for well-defined molecule classes, such assumptions cannot be safely generalised in ACC III. Based on our experience, we recommend protonating the structure using the following tools:

* *Hydride* ([https://hydride.biotite-python.org/](https://hydride.biotite-python.org/)) is a versatile command-line tool that supports all formats compatible with ACC III. Its main limitation is limited support for pH-dependent protonation. Hydride adds pH-dependent hydrogens only to standard amino acids in proteins, and protonation states are determined solely by comparing residue pKa values with the specified pH, without considering the local environment.

* *PDB2PQR* ([https://server.poissonboltzmann.org/](https://server.poissonboltzmann.org/)) is a specialised tool for adding hydrogens to proteins. It is available as both a command-line application and a web server. PDB2PQR supports protonation across a wide pH range and accounts for the local environment when determining protonation states. Its main limitation is that it only supports standard amino acids in proteins.


# Computation settings

Based on the molecules provided (in all files), methods and parameters that are suitable for all structures are displayed. The parameter set is suitable for a given input if it covers all the atomic types contained in the input files. A method is suitable if it has at least one suitable set of parameters or uses no parameters. Additionally, some methods (namely ABEEM, DelRe, DENR, KCM, MGC, and SQE*) might be omitted if the input contains at least one big molecule, i.e., one with over 20,000 atoms.

Automatic selection works in the same manner. After initial filtering described above, 3D methods are preferred over the 2D ones. When input contains protein structures, parameters for proteins are used (this is the case for EEM, which has the most parameters to choose from).

![setup](https://github.com/user-attachments/assets/e063b119-2547-416f-96ca-f0b35b308046)

All the methods and parameters have direct links to the original publications. The theoretical background of the methods is summarised in the standalone [PDF document](https://acc.biodata.ceitec.cz/methods.pdf). For easy identification, the name of the parameters used in a publication is enclosed in brackets.

# Results

The final page features the visualisation of the charges and the possibility to download the calculated charges. At the top, it states which method and parameters were used (useful when the automatic selection was used).

To switch between multiple structures or charges, the user can use the select box.

![results-select](https://github.com/user-attachments/assets/a4c0d168-5d36-4d20-8921-f9ede2864c83)

## Visualisation modes
ACC III features a fast Molstar viewer to visualise calculated charges. There are three standard modes the user can select – Balls and sticks, Cartoon, and Surface – see example (1F16):

<br>

<img src="https://github.com/sb-ncbr/AtomicChargeCalculator/blob/a0dc907ed85d91e2e2eecf0badaa9b33efe3b856/resources/github-images/1F16_bas.png" alt="bas" width="33%" />
<img src="https://github.com/sb-ncbr/AtomicChargeCalculator/blob/a0dc907ed85d91e2e2eecf0badaa9b33efe3b856/resources/github-images/1F16_cartoon.png" alt="cartoon" width="33%" />
<img src="https://github.com/sb-ncbr/AtomicChargeCalculator/blob/e01cfd9d4dda45cbd1d151efb7e66d8c78f35174/resources/github-images/1F16_surface_smooth.png" alt="surface" width="33%" />

<br>
<br>

The default is determined by the structure itself.
Note that to visualise mmCIF files, they must contain `_atom_sites category` (chemical components won’t work).

## Colouring options
Atoms are coloured by charge by default – red for negative charges and blue for positive ones.

In cartoon mode, the colour of individual residues is determined according to the sum of charges of all the atoms comprising them. In surface mode, the point on the surface of the molecule is coloured according to the nearest atom. Alternatively, colouring by charges can be disabled – colours are selected based on the elements.

## Downloading data
The charges are available in four formats – plain text, Mol2, PQR, and mmCIF. Plain text and mmCIF are present for all the inputs, PQR when the input contains structures with chain specification (most likely protein) and Mol2 otherwise (small molecules).

ACC III stores charges in custom mmCIF categories. For a complete reference, see the [extension dictionary](https://github.com/sb-ncbr/charges-schema).

# File management
After logging in, the user can filter, search, delete, and download uploaded files, or upload new ones until the quota is reached.
![file-management](https://github.com/user-attachments/assets/47b3ea44-0262-4b59-84d0-8d5c65610d3d)

Additionally, the user can select files and trigger a computation (similar to the process on the [Main page](#main-page)) through a dialogue.
![file-management-compute](https://github.com/user-attachments/assets/eeee9a2a-5c15-4ccf-85c0-603169ae2883)

# Calculation management
The calculation management page allows you to view, download, and delete previous calculations. Calculations are also limited by quota. Hovering over calculation or file badges will show additional information.
![calculation-management](https://github.com/user-attachments/assets/c0949ac3-51f5-4098-bea5-fd1d40cce1ba)

# API

For programmatic access, the ACC III API can be used. Below, we demonstrate the typical workflow for ACC III. See the [complete interactive documentation](https://acc.biodata.ceitec.cz/api/docs) containing a thorough description.

Certain operations (e.g., calculating partial atomic charges) require users to upload the necessary input files. If the upload is successful, users receive hashes of the file’s contents. These hashes can be referenced in subsequent operations. Additionally, successful charge calculations have a unique identifier (UUID), which is used to download an archive with results.

The following example uses `curl` to illustrate example HTTP requests for the abovementioned operations. Here, we upload multiple files simultaneously by specifying the -F option (form value) for each.

```bash
curl -X POST 'https://acc.biodata.ceitec.cz/api/v1/files/upload' \
  -H 'accept: application/json' \
  -H 'Content-Type: multipart/form-data' \
  -F 'files=@molecule1.sdf' \
  -F 'files=@molecule2.pdb'

# response
{
  "success": true,
  "data": [
    {
      "file": "molecule1.sdf",
      "fileHash": "<fileHash1>"
    },
    {
      "file": "molecule2.pdb",
      "fileHash": "<fileHash2>"
    }
  ]
}
```

The calculation of partial atomic charges usually follows. Users need to provide configurations, file hashes and settings parameters.

```bash
curl -X POST 'https://acc.biodata.ceitec.cz/api/v1/charges/calculate' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "configs": [
    {
      "method": "veem",
      "parameters": null
    }
  ],
  "fileHashes": [
    "<fileHash1>",
    "<fileHash2>"
  ],
  "settings": {
    "readHetatm": true,
    "ignoreWater": false,
    "permissiveTypes": true
  }
}'

# response
{
  "success": true,
  "data": "<comp_id>"
}
```

Finally, we can download the charges in a zip format, substituting `<comp_id>`:

```bash
curl -X GET 'https://acc.biodata.ceitec.cz/api/v1/files/download/computation/<comp_id>' \
  -H 'accept: application/zip' \
  -o charges.zip
```
# Limitations

To ensure stable and fair access for all users, the public web API is subject to reasonable usage limits. Users requiring large-scale calculations are encouraged to use [ChargeFW2](https://github.com/sb-ncbr/ChargeFW2) locally.

# Bug reporting

If you encounter an error, please send a report to tomas.racek@muni.cz or open a [GitHub issue](https://github.com/sb-ncbr/AtomicChargeCalculator/issues). Thank you!