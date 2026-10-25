# Deno redistribution simplification review

Reviewed 2026-10-25 for ClipThat!'s locked official Deno **2.9.8**, Linux x64 and Windows x64. This is a decision document; it does not authorize removing materials or change the release contract.

## Recommendation

**Replace per-release exhaustive collection with a reviewed, version-pinned redistribution-materials bundle, after closing its coverage gaps.** Keep required licenses, component-specific attribution/NOTICE material, and the small set of source archives needed for source obligations. Retain the existing collection as offline review evidence while preparing that bundle. Do not replace everything with Deno's MIT license.

Confidence is **high** that current collection substantially exceeds the source-distribution requirements established by the cited licenses. Confidence is **medium** in the proposed smaller bundle until its native-dependency and embedded-code coverage is reviewed. No complete, ready-to-use upstream Deno redistribution-notices bundle was identified in the inspected release assets and tagged repository. An upstream-provided complete bundle therefore cannot currently be treated as a drop-in replacement.

## Evidence and scope

Read `AGENTS.md`, `requirements.md`, `packaging/tools/README.md`, `scripts/collect_deno_materials.py`, and `packaging/tools/deno-materials-lock.json`. Inspected selected fields of the existing `build/deno-materials-verification/materials.json`, rather than opening its tens of thousands of notice payloads. Local inventory and collector code are implementation evidence, not independent upstream licensing statements.

The inventory reports:

| Item | Count |
| --- | ---: |
| Archives | 1,102 |
| Cargo component records | 1,188 |
| Unique registry crates | 1,079 |
| Native repository snapshots | 21 |
| Supplemental snapshots / distinct repositories | 80 / 57 |
| Notice records | 80,185 |
| Full attributed-source notice records | 77,440 |
| Named legal-file records | 2,321 |
| Supplemental repository legal-file records | 406 |
| Canonical license records / declared license-file records | 17 / 1 |

The previously observed footprint is approximately **1.41 GiB uncompressed**; this review did not remeasure it. `collection_complete` is true and `gaps`/`errors` are empty. These establish collector completion, not legal completeness. Approximately **96.6%** of notice records are entire source files selected by content matching, not distinct license documents. Their record share is not a measurement of byte savings.

### What the collector is protecting against

- It downloads every root Cargo.lock package, including development, unused and other-target packages, then Rust standard-library sources and their lock graph. This deliberately avoids needing an exact linked-package map.
- It follows rusty_v8's native gitlinks, including V8, ICU, Abseil, LLVM libraries, simdutf and build infrastructure. Deno's own source tarball is not assumed to include these sources.
- `scan()` retains full files whose names suggest legal material or whose contents contain copyright/SPDX/grant markers. This catches attribution embedded in source, at a large duplication/inode cost.
- `license_materials()` parses license alternatives, selects an alternative avoiding GPL-family obligations, retains canonical SPDX text, and records MPL source mappings. It does not establish all licenses of native code from Cargo metadata.
- Crates missing named license files cause supplemental repository legal-file collection. Unavailable SWC commits fall back to a recorded repository HEAD revision. This is explicitly supplemental evidence, not proof that the later revision's notices describe the published crate.
- The v8 crate's dirty-checkout metadata and absence of a complete official-binary link map remain documented limitations. More archives do not resolve either limitation.

The underlying concerns are real. The expensive mechanism is a conservative provenance policy, rather than a demonstrated requirement to ship every downloaded source archive and every source-containing notice file.

## Upstream findings

### 1. Deno's MIT grant is necessary but not a dependency notice bundle

[Deno v2.9.8 LICENSE.md][deno-license] requires preservation of its copyright and permission notice; it contains no general source-offer requirement. It does not enumerate binary dependencies.

The [official release API][release] lists binaries, checksums, binary patches, `deno_src.tar.gz`, and `lib.deno.d.ts`; no separately named complete third-party notice/license bundle is listed. Inspection of the full, non-truncated [tagged repository tree][deno-tree] found these license-named files outside tests: `LICENSE.md`, `cli/tsc/dts/node/LICENSE`, `cli/tsc/dts/node/undici/LICENSE`, and `ext/webgpu/LICENSE.md`. It found no named aggregate third-party-notices file. These searches do not prove there are no legal notices embedded elsewhere or inside executable data.

The [official npm packaging script][npm-build] copies the top-level MIT text into the wrapper package and extracts official binary ZIPs for platform packages. It does not generate a complete native/Rust dependency notice bundle. Its `license: MIT` package metadata is not evidence that all incorporated components have become MIT-only.

**Conclusion:** no verified complete upstream Deno bundle was found in those publication surfaces. Do not equate a source archive, repository license, or npm license field with such a bundle. Binary ZIP contents and any embedded legal-output facility were not independently audited here; obtaining an upstream-supported completeness statement remains a useful validation step.

### 2. V8 explicitly has additional licenses

The locked [rusty_v8 LICENSE][rusty-license] is MIT, but its [submodule declaration][gitmodules] references V8 and numerous separate native repositories. The matching [V8 LICENSE][v8-license] explicitly says externally maintained libraries have their own licenses, points to further subdirectory LICENSE files, and names embedded notices for some components.

V8's BSD terms require binary distributions to reproduce its copyright, conditions, and disclaimer in documentation or other accompanying materials. They do not require delivery of all V8 source. V8's own license also distinguishes test material from runtime-related code; collecting a repository's complete test/build tree is not evidence that those components are redistributed in Deno.

**Exact remaining native gap:** a reviewed mapping from the two official Deno binary assets to the applicable V8/native legal files, copyright notices, exceptions and data licenses. The current 21-snapshot set provides candidates, not that mapping. In particular, inspect ICU/data, Abseil, LLVM runtime libraries and their exceptions, simdutf, and V8's separately licensed in-tree code; do not assume the rusty_v8 MIT text covers them. Whether each candidate is actually incorporated is unresolved here.

### 3. Rust has a useful upstream-generated subset bundle

[Rust 1.95.0 COPYRIGHT][rust-copyright] describes its default Apache-2.0 OR MIT licensing, exceptions, REUSE in-tree metadata, and Cargo dependency metadata. It states that `generate-copyright` combines these into `COPYRIGHT.html`, shipped with Rust binary releases, and produces **`COPYRIGHT-library.html` specifically for the standard-library subset**.

This is a concrete upstream opportunity: use the matching standard-library copyright output and its referenced license texts instead of independently collecting the entire library lock graph merely to reconstruct notices. It is not a Deno-wide bundle, and the all-toolchain `COPYRIGHT.html` is a broader scope than needed.

**Validation required:** locate and pin the actual 1.95.0 library output (or generate it with that release's upstream tooling); check its contents and component/license references; establish which target standard-library/runtime inputs the official Deno builds used. The local toolchain pin identifies the declared Rust version, not independently every official binary's linked runtime object. Preserve source for any incorporated source-obligation component even if it appears in this notice output.

### 4. Notice generation is not source-obligation resolution

The tagged Deno [copyright checker][copyright-checker] checks first-party copyright headers and explicitly excludes several embedded third-party areas. It is not a third-party redistribution-notice generator. The inspected Deno/npm publication code provides no verified complete generated notice output. Rust's documented generator covers Rust, not Deno's Cargo graph plus V8 and embedded JS.

A replacement notice process therefore needs three inputs: Deno/embedded-code notices, Cargo component notices, and native/Rust material. Automatically concatenating SPDX license templates alone loses component-specific attribution and applicable NOTICE files. Conversely, shipping whole source files wherever a regex matches is not the only way to preserve the actual required legal text.

## Source requirements versus notices

These conclusions follow from the cited license texts; actual component applicability still requires review.

| License/material | Redistribution consequence | Source consequence |
| --- | --- | --- |
| Deno/rusty_v8 MIT | Preserve applicable copyright and permission notice, including warranty text in the license | No general source-delivery requirement in that grant |
| V8 BSD terms | Preserve copyright, conditions and disclaimer with binary distribution; respect non-endorsement term | No general obligation to distribute all source |
| Apache-2.0 | Give recipients the license; preserve applicable NOTICE attribution under §4(d); follow modification/source-notice conditions where applicable | §4 permits Object-form distribution without a general requirement to deliver source |
| MPL-2.0 | Inform executable recipients how to obtain covered source, preserve applicable notices and source rights | §3.2 requires covered Source Code Form to be available by reasonable means in a timely manner; §3.3 permits a larger work under other terms |
| Native/data licenses and exceptions | Apply the actual component's terms, not Cargo's wrapper declaration | Resolve individually before dropping source; not all are established by this review |

Primary texts: [MIT][deno-license], [V8 BSD][v8-license], [Apache-2.0 §4][apache], [MPL-2.0 §§3.1–3.4][mpl]. Retaining matching full crate archives for MPL components is a simple conservative fulfillment method; MPL does not thereby require all unrelated Deno/V8/build-tool sources. A notices-only bundle cannot replace covered source availability.

The current manifest records MPL source obligations for **cooked-waker 5.0.0, cssparser 0.36.0, cssparser-macros 0.6.1, dtoa-short 0.3.5, smartstring 1.0.1, and fortanix-sgx-abi 0.6.1**. This is the collector's selected-license inventory, not a claim that all six ship in both official binaries or that these are all native obligations. Initially retaining all six matching archives is lower-maintenance than proving exclusions. Do not infer actual distribution from a root lockfile entry alone.

## Concrete options

### A. Reviewed bundle once per Deno pin — recommended

1. Reuse the existing verified collection as review input; do not repeat the 1,102-archive crawl on every platform release.
2. Produce one immutable bundle for 2.9.8 covering both supported targets: Deno MIT; reviewed embedded-code notices; attributed Cargo licenses/NOTICE material; native/V8 notices; matching Rust standard-library legal output; conservative MPL source archives; and a short source-access document.
3. Use one small inventory recording component/version, upstream revision or checksum, selected license, notice path and any source archive. Preserve attribution associations even when identical license text is stored once. Keep explicitly unresolved entries visible until resolved.
4. Release preparation downloads or copies that hash-pinned bundle, verifies it against the binary/version pins, and stages its notices and required sources. Perform coverage review when the Deno pin changes, not on every native app build.

**Confidence:** high engineering benefit; medium completeness until the gaps above close. No exact size saving is claimed without assembling the reviewed bundle. The lowest-maintenance first cut can preserve the Cargo notice superset while removing redundant entire source-file copies only after extracting their required legal content, and retain all six MPL archives.

### B. Cache the existing complete output — immediate conservative bridge

Prepare the current verified collection once per lock fingerprint and reuse it through the existing `--deno-materials` mechanism. This avoids repeated network/tree work without a legal-material removal decision. It preserves the storage, copy and inode cost, plus current provenance limitations. **Confidence: high** for operational simplification, low for footprint improvement.

### C. Upstream-supported aggregate bundle — preferred if obtainable

Ask Deno maintainers for a versioned notice/license bundle covering official target binaries, including native dependencies and Rust, with source locations for covered components. If supplied, review its scope and exceptions once, then pin it. **Confidence: presently unavailable as a verified replacement** in the inspected surfaces. A generic MIT file, Cargo-only report, or Rust-only copyright output does not meet this scope.

Building Deno from source solely to obtain a link map adds a toolchain/native-build maintenance burden and is not the focused simplification recommended here.

## Acceptance criteria before removing current payloads

- Review the candidate bundle against the existing inventory by component and obligation, rather than requiring equality with 80,185 regex-selected records.
- Close native/V8 coverage, embedded TypeScript/Node/polyfill/data notices, Rust-library output, and unavailable-commit supplemental-notice gaps. Record exclusions as target/build evidence, not filename guesses.
- Preserve actual copyright holders, component-specific grants, NOTICE text, exceptions, and required source; canonical SPDX templates alone are insufficient evidence.
- Check source-access instructions point to retained matching archives and remain available with the release. Keep the current conservative MPL set until any exclusion is justified.
- Keep exact official binary hashes, material-bundle hash and version matching. Integrity validation must not claim legal certification.
- Obtain the parent reviewer's explicit decision on policy changes and subsequent updates to validators, packaging layout and contract documents. No payload removal is implemented by this review.

No tests, builds, commits, publication, or runtime/build-script changes were performed for this docs-only review.

## Primary sources

[deno-license]: https://raw.githubusercontent.com/denoland/deno/v2.9.8/LICENSE.md
[release]: https://api.github.com/repos/denoland/deno/releases/tags/v2.9.8
[deno-tree]: https://api.github.com/repos/denoland/deno/git/trees/v2.9.8?recursive=1
[npm-build]: https://raw.githubusercontent.com/denoland/deno/v2.9.8/tools/release/npm/build.ts
[copyright-checker]: https://raw.githubusercontent.com/denoland/deno/v2.9.8/tools/copyright_checker.js
[rusty-license]: https://raw.githubusercontent.com/denoland/rusty_v8/5c15a6995c9bb4bacd3e341b59fff32c909c80bf/LICENSE
[gitmodules]: https://raw.githubusercontent.com/denoland/rusty_v8/5c15a6995c9bb4bacd3e341b59fff32c909c80bf/.gitmodules
[v8-license]: https://raw.githubusercontent.com/denoland/v8/ac1e23989121713ca642f6650b34deff7b686896/LICENSE
[rust-copyright]: https://raw.githubusercontent.com/rust-lang/rust/1.95.0/COPYRIGHT
[apache]: https://www.apache.org/licenses/LICENSE-2.0.txt
[mpl]: https://www.mozilla.org/en-US/MPL/2.0/

All external licensing assertions above are grounded in official project/steward files, publication scripts, or APIs. Absence findings are bounded to the inspected surfaces; upstream binary completeness and legal applicability remain distinct from the local collector's mechanical status.
