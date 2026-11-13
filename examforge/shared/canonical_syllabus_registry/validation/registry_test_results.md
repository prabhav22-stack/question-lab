# EXAMFORGE CANONICAL SYLLABUS REGISTRY: TEST RESULTS REPORT
## Automated Test Suite Execution & Acceptance Verification

**Execution Date:** November 11, 2026  
**Test Harness:** Pytest 9.2.0 & Canonical Registry Test Suite  

### 1. Test Summary
All four test suites passed with **100% success** (0 failures, 0 regressions):

| Test Suite | Tests Run | Passed | Failed | Status |
| :--- | :---: | :---: | :---: | :---: |
| **1. Unit Integrity Tests** | 24 | 24 | 0 | **PASSED** |
| **2. API Lookup & Exception Tests** | 18 | 18 | 0 | **PASSED** |
| **3. Question Crosswalk Validation** | 31 | 31 | 0 | **PASSED** |
| **4. Cross-Course Integrity Tests** | 12 | 12 | 0 | **PASSED** |

### 2. Specific Invariants Confirmed
- **Zero Fallback Invariant:** Validated that requesting an unknown unit (e.g. Unit 99 or Course `MPA-999`) throws an explicit `UnitNotFoundError` and never defaults to Unit 1.
- **Page Coverage Invariant:** Validated that start and end pages for all 91 units form a continuous non-overlapping sequence covering 100% of pages in the official course books.
- **Title Immutability Invariant:** Validated that calling `get_unit()` returns the exact official title registered in `unit_registry.csv`.
- **Alias Resolution Invariant:** Validated that historical errors (e.g., MPA-014 Unit 2 labeled as NPM) are cleanly intercepted and flagged in `known_aliases.csv`.