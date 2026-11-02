# Data check

Sources: openi = real chest X-ray reports; plaba = PubMed abstracts (not clinical reports); synthetic = template-generated (must be labeled synthetic in the paper).

| source | n | tokens med/p95/max | fit 512 | hedged | numeric | hedge+number | recommend | XXXX |
|---|---|---|---|---|---|---|---|---|
| openi | 3159 | 67/134/332 | 3159 (100.0%) | 608 (19.2%) | 141 (4.5%) | 68 (2.2%) | 156 (4.9%) | 1612 (51.0%) |
| plaba | 749 | 329/608/1244 | 657 (87.7%) | 282 (37.7%) | 406 (54.2%) | 155 (20.7%) | 176 (23.5%) | 0 (0.0%) |
| synthetic | 50 | 63/71/72 | 50 (100.0%) | 46 (92.0%) | 50 (100.0%) | 46 (92.0%) | 50 (100.0%) | 0 (0.0%) |

openi fully normal (heuristic): 1213 (38.4%)

## Gate
- [x] >=300 hedged clinical reports, openi+synthetic (654)
- [x] >=150 numeric clinical reports, openi+synthetic (141 real + 50 synthetic = 191)
- (info) numeric incl. PLABA abstracts: 597
- [x] >=95% of openi reports fit 512 tokens (100.0%); PLABA fit: 87.7%
- [ ] hedge detector precision >=0.85 on 50 hand-checked sentences (manual)
- [ ] baseline smoke run shows measurable error rate (manual)

## Hedge term counts (openi)
- consistent with: 142
- may be: 114
- may represent: 111
- compatible with: 93
- possibly: 50
- suggestive of: 47
- probable: 46
- possible: 42
- indeterminate: 36
- could be: 31
- could represent: 29
- concerning for: 24
- probably: 21
- suggests: 18
- questionable: 14
- cannot be excluded: 9
- cannot exclude: 7
- suspicious for: 6
- not excluded: 3
- cannot be ruled out: 1

## 10 random hedged openi reports
- **3278**: FINDINGS: Chest: 2 images. Heart size is normal. Mediastinal contours are maintained. There is a mild pectus excavatum deformity. The lungs are clear of focal infiltrate. There is no evidence for pleural effusion or pneumothorax. No convincing acute bony findings. Right shoulder: 3 images. There has been XXXX and screw fixation of the midshaft right clavicle. The lateral most screw is fractured. This is age-indeterminate as no prior studies are available for comparison. Otherwise, the surgical XXXX appears intact. The humeral head is seen within the glenoid, without evidence for dislocation. No bony fractures are seen. The visualized right ribs appear intact. Right clavicle: 2 images. No clavicle fracture is seen. Once again noted is the surgical fixation XXXX, with fracture of the lateral most fixation screw. IMPRESSION: Chest: 1. No acute cardiopulmonary abnormality identified. 2. Pectus excavatum. Right shoulder and right clavicle: 1. No acute bony abnormality identified. 2. The lateral most screw of the clavicular fixation XXXX is fractured. This is age-indeterminate as no prior studies are available for comparison. Clinical correlation is XXXX.
- **350**: FINDINGS: Normal cardiomediastinal contours. No pneumothorax or large pleural effusions. Left basilar patchy opacities. Small hiatal hernia. IMPRESSION: Left basilar patchy opacities, which may represent atelectasis or infection. .
- **1181**: FINDINGS: The central venous line has been removed. An inflammatory defibrillator is noted. The heart is enlarged. The patient is status post XXXX sternotomy. Right pleural effusion is present and unchanged. No pneumothorax is seen. There has been clearing of the left base airspace disease. Some continued right lung opacities are present which may represent areas of scarring. IMPRESSION: 1. Cardiomegaly without overt heart failure. 2. Small right pleural effusion. No change. 3. Clearing of left base airspace disease. 4. Improvement in right lung airspace disease.
- **2421**: FINDINGS: The heart is enlarged. The left subclavian ICD is again identified. There is again hilar enlargement, XXXX superimposes enlarged pulmonary vasculature. XXXX opacities are unchanged and compatible with subsegmental atelectasis or scarring. There is no large pleural effusion or focal consolidation. IMPRESSION: Stable moderate to marked cardiomegaly.
- **424**: FINDINGS: The lungs are clear. There is no focal consolidation, pleural effusion, or pneumothorax. The Heart and mediastinum are normal size and shape. XXXX and soft tissues are unremarkable. Probable nerve stimulator noted. IMPRESSION: No Acute cardiopulmonary disease.
- **3891**: FINDINGS:  IMPRESSION: Heart size normal.No significant change in left base airspace disease and small effusion. Small residual right pneumothorax. Increased right base atelectasis.Catheter overlying the right mediastinum may be outside the patient is.
- **343**: FINDINGS: Heart size and mediastinal contour are normal. Pulmonary vascularity is normal. is not diffuse interstitial prominence, which has chronic appearance. Cannot exclude early pulmonary edema. Two airspace consolidation or effusion. XXXX are osteopenic. No visible pneumothorax. IMPRESSION: Mild interstitial prominence, XXXX chronic though could reflect early pulmonary edema.
- **2733**: FINDINGS: Bibasilar airspace opacities, right greater than left. The heart size and mediastinal silhouette are within normal limits for contour. No pneumothorax or pleural effusions. The XXXX are intact. IMPRESSION: Bibasilar airspace opacities, right greater than left. These findings are concerning for pneumonia.
- **3865**: FINDINGS: The heart is top normal in size. The mediastinum is stable. The lungs are grossly clear. Bilateral rib deformities are noted, possibly old fractures. There is no pleural effusion or pneumothorax. IMPRESSION: No acute disease.
- **3107**: FINDINGS: Upper mediastinal mass on the right has increased in opacity with some pressure on the right side of the trachea in the interval. No masses or infiltrates in the lungs. Heart and XXXX remain normal. IMPRESSION: Increasing upper mediastinal mass, probably a goiter. Clear lungs.
