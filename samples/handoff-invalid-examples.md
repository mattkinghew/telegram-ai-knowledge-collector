# Invalid mobile handoff examples

These examples are descriptions, not importable files:

- missing any required field, even when its value would be empty;
- unknown `attachment` field;
- duplicate `title` JSON key;
- top-level array or nested object/array;
- `null`, Boolean, or number used for a string field;
- schema version other than integer `1`;
- newline in a single-line field;
- invalid `YYYY-MM-DD` date;
- `captured_at` without `Z` or an explicit timezone offset;
- text or voice transcript with empty content;
- non-empty `source_url` for text or voice transcript;
- URL handoff without HTTP/HTTPS URL;
- URL with embedded username or password;
- file larger than 256 KB, non-UTF-8, symlink, directory, or non-JSON suffix;
- array or folder intended for batch import.

The CLI does not accept attachments, audio, batch payloads, automatic imports,
or unknown future fields.
