# Generate BOM for E-CAD Projects

Generate a BOM output file for Altium, OrCAD or System Capture projects on
AllSpice Hub using
[AllSpice Actions](https://learn.allspice.io/docs/actions-cicd).

## Usage

Add the following steps to your actions:

```yaml
# Checkout is only needed if columns.yml is committed in your Altium project repo.
- name: Checkout
  uses: actions/checkout@v3

- name: Generate BOM
  uses: https://hub.allspice.io/Actions/generate-bom@v0.6
  with:
    # The path to the project file in your repo.
    # .PrjPcb for Altium, .DSN for OrCad, .SDAX for System Capture.
    source_path: Archimajor.PrjPcb
    # [optional] A path to a YAML file mapping columns to the component
    # attributes they are from.
    # Default: 'columns.yml'
    columns: .allspice/columns.yml
    # [optional] The path to the output file that will be generated.
    # Default: 'bom.csv'
    output_file_name: bom.csv
    # [optional] A comma-separated list of columns to group the BOM by. If empty
    # or not present, the BOM will be flat.
    # Default: ''
    group_by: "Part ID"
    # [optional] The variant of the project to generate the BOM for. If empty
    # or not present, the BOM will be generated for the default variant.
    # Default: ''
    variant: ""
```

### Customizing the Attributes Extracted by the BOM Script

This script relies on a YAML file to specify the columns in the BOM and which
attributes or properties of the components they are populated from. This file is
typically called `columns.yml` and can be checked into your repo. To learn more
about YAML, [check out the AllSpice Knowledge Base.](https://learn.allspice.io/docs/yaml)

The format of this YAML file is as follows:

```yml
columns:
  - name: "Manufacturer"
    part_attributes:
      - "Manufacturer"
      - "MANUFACTURER"
  - name: "Part Number"
    part_attributes:
      - "PART"
      - "MANUFACTURER #"
      - "_part_id"
  - name: "Designator"
    part_attributes: "Designator"
  - name: "Description"
    part_attributes:
      - "PART DESCRIPTION"
      - "_description"
```

First, you have the key `columns:` which is mapped to a list. Each element of
the list has two key/value pairs. The first is `name`, which will be the column
name in the output file. Next, you have `part_attributes`. This can either be
just a string (like in the case of the `Designator` column) or a list of strings
(like in the other cases).

If `part_attributes` is a string, that property or attribute of the component
is used as the value for that column. If that property is not present
in a particular part, that column will be blank for that part. If
`part_attributes` is a list, those properties will be checked in the order they
are defined for each part. The _first_ property found is used as the value for
that column in the row for that part. So if both `PART` and `MANUFACTURER #` are
defined, it will use `PART`.

An example for OrCad `columns.yml` file content is:

```yml
columns:
  - name: "Part Number"
    part_attributes:
      - "Part Number"
      - "_name"
  - name: "Designator"
    part_attributes: "Part Reference"
  - name: "Type"
    part_attributes: "Part Type"
  - name: "Value"
    part_attributes: "Value"
```

By default, the action will pick up a `columns.yml` file from the working
directory. If you want to keep it in a different place or rename it, you can
pass the `--columns` argument to the step in the workflow to specify where it
is.

### Py-allspice injected attributes

Note that py-allspice also adds a few static attributes, which are taken from
the part itself, and not from the properties or attributes. For Altium projects,
`_part_id` and `_description` are available, which correspond to the Library
Reference and Description fields of the component. For OrCAD and System Capture
projects, `_name` is available, which corresponds to the name of the component.

The underscore is added ahead of the name to prevent these additional attributes
from overriding any of your own.

### Customizing sorting, filtering and grouping

If you need more control over the BOM, you can configure each column with the
following attributes. You can mix and match as many of these configuration
options as you want.

#### Sorting

Add the `sort` attribute to a column to sort the BOM by that column. The value
of the attribute should be `asc` or `desc`.

```yaml
columns:
  - name: "Part Number"
    part_attributes:
      #  - "Part Number"
      - "_name"
    sort: "asc"
```

If multiple columns have the `sort` attribute, the BOM will be sorted by the
columns in the order they are defined.

The default is no sorting. In that case, the order of the BOM is not specified.

#### Filtering

To filter the BOM based on a column, add a Regular Expression pattern to the
`remove_rows_matching` attribute of a column. As the name indicates, every row
where the value of the specified column matches this regex will be removed from
the BOM.

```yaml
columns:
  - name: "Part Number"
    part_attributes:
      - "Part Number"
      - "_name"
    # This will remove all rows where the part number has either "TP", "MTG" or
    # "FID" anywhere in it, i.e. will remove all the test points, mounting
    # holes and fiducials.
    remove_rows_matching: "TP|MTG|FID"
```

Since this is a regular expression, you can make fairly complex filters. You
can read more about regular expressions
[here](https://docs.python.org/3/library/re.html#regular-expression-syntax).

By default, there is no filtering.

#### Grouped Values Configuration

You can use the `grouped_values_sort`, `grouped_values_separator` and
`grouped_values_allow_duplicates` attributes to configure the grouped values of
a column. To understand these better, consider the case of a BOM which is grouped
by Part Number, and you want to have a column that lists all the Designators of
a part with the same Part Number. You want the designators to be separated by
a space, and you want them sorted in ascending order. You also want repeated
designators to appear in the list.

```yaml
columns:
  - name: "Part Number"
    part_attributes:
      - "Part Number"
      - "_name"
  - name: "Designators"
    part_attributes: "Designator"
    grouped_values_sort: "asc"
    grouped_values_separator: " "
    grouped_values_allow_duplicates: true
```

By default:

- Grouped values are not sorted, and the order is not specified.
- Grouped values are separated by a comma.
- Grouped values do not allow duplicates.

#### Skip in output

If you need an attribute to just filter, sort or group by, but not show in the
BOM output, you can use the `skip_in_output` attribute.

```yaml
columns:
  - name: "BOM Ignore"
    part_attributes:
      - "BOM_IGNORE"
    remove_rows_matching: ".*"
    skip_in_output: true
```

### Design Reuse repositories

For Altium projects, if you are using device sheets that are located in a
different repository, you can set a list of design reuse repositories. These
repositories are tried in order to find device sheets that are not in the
project, i.e. the first repository to contain a file that has the same name as
a device sheet will be used for that device sheet. If you are using design
reuse repositories, you MUST set a custom auth token, as the default one may
not have the permissions to fetch other repositories.

An example for the `columns.yml` file content is:

```yml
columns:
  # ...
design_reuse_repos:
  - "Archimajor/DesignReuseRepo"
  - "Archimajor/DesignReuseRepo2"
  - "Archimajor/DesignReuseRepo3"
```

In this case, for each device sheet that is not in the project, the action will
check each of `Archimajor/DesignReuseRepo`, `Archimajor/DesignReuseRepo2` and
`Archimajor/DesignReuseRepo3` in order to find the device sheet, and the first
match found will be used.

Currently, the latest commit on the default branch of the repo is the ref used
to match the files.

### Group By

You can also group lines by a column value. The most common is `_part_id`. You
can combine this with the columns YAML example above, like so:

```yaml
- name: Generate BOM
  uses: https://hub.allspice.io/Actions/generate-bom@v0.6
  with:
    project_path: Archimajor.PrjPcb
    columns: .allspice/columns.yml
    group_by: "Part ID"
```

Which will generate a BOM squashed by components with matching Part IDs.

### Variants

To generate the BOM for a variant of the project, pass the `--variant` argument
to the script. For example:

```yaml
- name: Generate BOM
  uses: https://hub.allspice.io/Actions/generate-bom@v0.6
  with:
    project_path: Archimajor.PrjPcb
    columns: .allspice/columns.yml
    output_file_name: bom-lite.csv
    variant: "LITE"
```

When no variant is given, the BOM is generated without considering any variants.

### SSL

If your instance is running on a self-signed certificate, you can tell the action
to use your certificate by setting the `REQUESTS_CA_BUNDLE` environment variable.

```yaml
- name: Generate BOM
  uses: https://hub.allspice.io/Actions/generate-bom@v0.6
  with:
    project_path: Archimajor.PrjPcb
    columns: .allspice/columns.yml
    output_file_name: bom.csv
    variant: "LITE"
  env:
    REQUESTS_CA_BUNDLE: /path/to/your/certificate.cert
```

### Custom Auth token

By default, this action uses the auto-generated auth token for the run.
However, this auth token may not have all the permissions you need, e.g. if you
have design reuse repos. In that case, you can customize the auth token used by
setting the `auth_token` input.

```yaml
- name: Generate BOM
  uses: https://hub.allspice.io/Actions/generate-bom@v0.6
  with:
    project_path: Archimajor.PrjPcb
    columns: .allspice/columns.yml
    output_file_name: bom.csv
    variant: "LITE"
    auth_token: ${{ secrets.ALLSPICE_AUTH_TOKEN }}
```
