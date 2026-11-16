# Investigation audit and export — Milestone 21

Every investigation now includes an audit identity:

- A unique run ID and UTC generation timestamp
- A SHA-256 fingerprint of the canonical question, scenario inputs, knowledge scope, and evidence IDs
- A named simulation model version
- A reproducibility note explaining what the fingerprint does and does not prove

The fingerprint is designed to identify the recorded inputs. It is not a digital signature, proof that the inputs are truthful, or a guarantee that outputs will remain identical if optional local model settings or source documents change.

## PDF export

`POST /agents/investigate/report.pdf` accepts the completed investigation response and returns a PDF containing the question, district, projected indicators, ranked options, specialist consensus and dissent, verification status, evidence IDs, audit fingerprint, and limitations. The endpoint exports the supplied result; it does not rerun the investigation. Private document text is not included in the report; only the knowledge scope and evidence identifiers are shown.

The public frontend adds a **Download investigation audit PDF** action after a successful public investigation. Private workspace investigation results can also be exported by submitting their response JSON to the same export endpoint, but the current private UI does not yet expose that control.

## Boundaries

- This is an audit aid, not tamper-proof logging. A client can edit a submitted result before export.
- SHA-256 is used for input fingerprinting, not signing or user identity verification.
- All city data remains synthetic and the report is not an engineering approval.
