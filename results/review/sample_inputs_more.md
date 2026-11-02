# More sample inputs for the demo

Real reports are from the public Open-i chest X-ray collection and come only from the held-out test split. Reports marked SYNTHETIC were written by our generator and are not real patients. Rebuild with `scripts/make_sample_inputs.py`.

## Normal study (nothing to explain)

id: `3377`  (real, Open-i)

```
FINDINGS: PA and lateral views were obtained. Lungs are clear. There is no pneumothorax or pleural effusion. The heart and mediastinum are within normal limits. Bony structures are intact. IMPRESSION: No acute cardiopulmonary process. If patient's symptoms persist recommend repeat study XXXX chest in one XXXX.
```

id: `3534`  (real, Open-i)

```
FINDINGS: Lungs are clear bilaterally. There is no focal consolidation, pleural effusion, or pneumothoraces. Heart size is normal. Stable right paratracheal prominence, consistent with known calcified lymph node, seen on prior CT chest dated XXXX. XXXX are unremarkable. IMPRESSION: No acute cardiopulmonary abnormality.
```

## 'Possible' / 'cannot be excluded' hedges

id: `101`  (real, Open-i)

```
FINDINGS: The heart is again mildly enlarged. Mediastinal contours are stable. Patient is somewhat rotated. The lungs are hypoinflated with elevated left hemidiaphragm. XXXX XXXX opacities compatible with atelectasis. No large effusion is seen. There is no focal consolidation. Pulmonary vascularity is mildly accentuated. There are bilateral degenerative changes of the XXXX with probable chronic dislocation of the left humerus. Correlate clinically. IMPRESSION: 1. Mild stable cardiomegaly and central vascular congestion. 2. Low lung volumes with elevated left hemidiaphragm and basilar subsegmental atelectasis. 3. Extensive bilateral shoulder degenerative changes with subluxation/dislocation left shoulder, possibly chronic. Suggest clinical correlation.
```

id: `1210`  (real, Open-i)

```
FINDINGS: The heart, pulmonary XXXX and mediastinum are within normal limits. There is no pleural effusion or pneumothorax. There is no focal air space opacity to suggest a pneumonia. There mild degenerative changes of the thoracic spine. There is a slight XXXX deformity of the lower thoracic body which is age-indeterminate. IMPRESSION: Age-indeterminate lower thoracic slight XXXX deformity otherwise negative exam.
```

id: `123`  (real, Open-i)

```
FINDINGS: Mild cardiomegaly. Tortuous aorta. No focal infiltrate. No pneumothorax or large pleural effusion. Soft tissue density identified in the medial right apex which is asymmetric compared to left. IMPRESSION: Asymmetric right medial apical opacity which may be attributable to the sternoclavicular joint. Upper lobe airspace disease or pulmonary nodule is not entirely excluded. Recommend XXXX XXXX chest and apical lordotic view of the chest to further evaluate. Findings and recommendations were discussed XXXX. XXXX in the XXXX department at XXXX a.m. XXXX/XXXX.
```

id: `1230`  (real, Open-i)

```
FINDINGS: IMPRESSION: Left lung clear. Slight cardiomegaly. Right effusion. Right lower lobe infiltrate. Two air-fluid levels in the right hemithorax most XXXX representing hydropneumothorax. This radiographic finding could also represent empyema with a bronchopleural fistula. CT scan with IV contrast may be helpful.
```

## 'Likely' / 'consistent with' hedges

id: `1056`  (real, Open-i)

```
FINDINGS: Normal heart size. Stable tortuous aorta. No pneumothorax or pleural effusion. No suspicious focal air space opacities. Levoscoliosis of the thoracolumbar spine. Hyperinflated lungs with flattened diaphragms are consistent with emphysematous lung changes. Prior granulomatous disease. IMPRESSION: Stable emphysematous lung changes. No acute abnormality seen.
```

id: `1117`  (real, Open-i)

```
FINDINGS: The cardiomediastinal silhouette and pulmonary vasculature are within normal limits in size. There is ill-defined airspace opacity in the posterior left lower lobe. There is focal opacity in the right upper lobe which suggests scar and/or granulomatous calcification. There is no pneumothorax or pleural effusion. IMPRESSION: 1. Patchy left lower lobe airspace disease, concerning for pneumonia. 2. Right upper lobe opacity, favoring scarring and/or granulomas. .
```

id: `112`  (real, Open-i)

```
FINDINGS: Previous lower spine cervical fusion. Lungs are overall hyperexpanded with flattening of the diaphragms consistent with obstructive lung disease. Lungs are clear without focal consolidation. No pleural effusions or pneumothoraces. Heart and mediastinum of normal size and contour. Degenerative changes in the spine. IMPRESSION: Hyperexpanded but clear lungs.
```

id: `1160`  (real, Open-i)

```
FINDINGS: The left hilum is retracted superiorly. In the collapsed left upper lobe are stranding and pneumatoceles. Additionally, pleural thickening is present in the left apex. No infiltrates are present in the left lower lobe or in the right lung. Heart size is normal. These findings are similar to the previous outside examination. IMPRESSION: Stable left upper lobe collapse associated with parenchymal scarring and pleural thickening. Findings consistent with previous active pulmonary tuberculosis pneumonia.
```

## Measurements that must survive

id: `1329`  (real, Open-i)

```
FINDINGS: Two nodules are noted in the right XXXX XXXX measuring 13 mm and one measuring 16 mm in diameter. The smaller one appears to be within the right upper lobe and the large XXXX appears to be within the left lower lobe. No focal consolidation and no other pulmonary nodules are identified. However, if a full evaluation for lung nodules is desired consider XXXX for further evaluation. No pleural effusions or pneumothoraces. Heart and mediastinum of normal size and contour. IMPRESSION: At XXXX 2 right lung pulmonary nodules concerning for<BR>metastatic disease
```

id: `1668`  (real, Open-i)

```
FINDINGS: No pneumothorax, pleural effusion, or focal airspace disease. There is a discrete 1.4 cm nodule within the anterior segment of the right lower lobe. The additional nodular opacities consistent with chronic granulomatous disease. Heart size normal. Cardiomediastinal silhouette is clear. Bony structures appear intact. Right unilateral nipple ring. IMPRESSION: 1. Negative for acute cardiopulmonary disease. 2. 1.4 cm right lower lobe nodule, XXXX calcified granulomas disease. If patient high XXXX for pulmonary malignancy, consider cross-sectional imaging to verify.
```

## Left and right both mentioned

id: `1326`  (real, Open-i)

```
FINDINGS: IMPRESSION: Stable right-sided subclavian central venous catheter with tip approximating the SVC. Stable right suprahilar opacity, compatible with history of right upper lobe mass. Elevation of the right hemidiaphragm. Right-sided pneumothorax noted measuring approximately 1.8 cm from the the right apex. Stable postsurgical changes left axilla. Degenerative changes thoracic spine. Stable streaky opacities right base. XXXX opacity right midlung, question fluid level, incompletely evaluated, no recent XXXX for comparison.
```

id: `1370`  (real, Open-i)

```
FINDINGS: Stable cardiomediastinal silhouette. There is mild haziness in the right lung and left base, which could represent infiltrate. No pleural effusion. No pneumothorax. Stable XXXX deformity of a midthoracic vertebra. IMPRESSION: 1. Possible infiltrates in the right lung and left base. Consider CT for further evaluation, if clinically indicated.
```

id: `1506`  (real, Open-i)

```
FINDINGS: There is interval placement of a XXXX on the left chest with the catheter tip in the cavoatrial junction. The heart size is within normal limits. Lung volumes within normal limits. Slightly prominent pulmonary vascularity noted. Increased peribronchial cuffing. No large consolidation, effusion, or pneumothorax. There is subpleural edema outlining the right XXXX fissure. IMPRESSION: 1. Stable and adequately placed XXXX. 2. Prominent pulmonary vasculature, subpleural edema, and peribronchial cuffing suggestive of volume overload versus viral bronchiolitis.
```

id: `1534`  (real, Open-i)

```
FINDINGS: The cardiomediastinal silhouette is normal in size and contour. Aortic atherosclerosis. Hyperexpanded lungs. XXXX right perihilar/midlung density. Streaky bibasilar opacities, as well. Left upper lobe nodular opacity (anterior first rib interspace) may be exaggerated by overlapping bone silhouettes. Grossly similar midthoracic vertebral XXXX fracture. IMPRESSION: 1. No focal air space consolidation. 2. Nodular opacity at the left apex may be exaggerated by overlapping bone silhouettes. XXXX chest may provide further evaluation, if warranted.
```

## Follow-up recommended

id: `1416`  (real, Open-i)

```
FINDINGS: The cardiac silhouette is at the upper limits of normal for size. Stable, mild prominence of the bilateral hilar regions. No focal areas of pulmonary consolidation. No pneumothorax. Stable XXXX opacity in the left XXXX, XXXX representing a scar. No pleural effusion. Minimal degenerative changes of the thoracic spine. No acute, displaced rib fractures. IMPRESSION: 1. No acute intrathoracic abnormality. 2. Stable, mild prominence of the bilateral hilar regions, possibly consistent with enlarged pulmonary arteries/pulmonary hypertension. Please correlate clinically.
```

id: `1676`  (real, Open-i)

```
FINDINGS: Heart size and mediastinal contour within normal limits. Aortic atherosclerotic calcifications. Emphysematous changes. Nodular densities projecting over right anterior fifth and six ribs. No focal airspace consolidation, pneumothorax, or large pleural effusion. No acute osseous abnormality. IMPRESSION: Nodular densities projecting over right 5th and 6th ribs may healing rib fracture; XXXX recommended to rule-out underlying pulmonary nodule. XXXX level Veriphy message was sent XXXX. XXXX regarding possible lung nodules at XXXX hours XXXX/XXXX.
```

id: `1925`  (real, Open-i)

```
FINDINGS: The heart is normal in size. There is bihilar prominence. The lungs are clear. IMPRESSION: Bihilar prominence may be secondary mild lymphoid enlargement. Followup chest x-XXXX versus further imaging XXXX may be indicated. Correlation with prior films would be helpful if available.
```

id: `2111`  (real, Open-i)

```
FINDINGS: Patchy airspace disease is present in the lateral view probably within the right lower lobe. There is severe underlying emphysema. The aorta is calcified. There is spondylosis. IMPRESSION: Patchy airspace disease on the lateral view, probably within the right lower lobe, XXXX a pneumonia superimposed on XXXX severe underlying emphysema. Recommend following this process to resolution.
```

## Short and simple

id: `1289`  (real, Open-i)

```
FINDINGS: One XXXX are low. Both costophrenic XXXX are blunted. Pulmonary XXXX are normal. No visible infiltrates in the aerated lungs. IMPRESSION: Bilateral large pleural effusion, possibly from pleuritis or sympathetic from the known pancreatitis.
```

id: `1389`  (real, Open-i)

```
FINDINGS: IMPRESSION: Heart size is normal. Lungs are clear. Overexpanded lungs suggests emphysema. No nodules masses or effusions
```

id: `1494`  (real, Open-i)

```
FINDINGS: IMPRESSION: Decreasing lung volumes. Probable bilateral pleural effusions and elevation of both hemidiaphragms.
```

id: `1712`  (real, Open-i)

```
FINDINGS: Normal cardiac contours. No pleural effusion or pneumothorax. Bilateral lower lobe bronchial thickening consistent with bronchitis. IMPRESSION: 1. Bilateral lower lobe bronchitis.
```

## Long, many findings

id: `1167`  (real, Open-i)

```
FINDINGS: The lungs are hyperexpanded. There are XXXX opacities in the lingula, XXXX subsegmental atelectasis or scarring. There is no focal airspace consolidation. No pleural effusion or pneumothorax. Heart size is within normal limits. There is aortic atherosclerotic vascular calcification. There are degenerative changes of the spine. IMPRESSION: 1. No focal airspace consolidation. 2. Hyperexpanded lungs, suggestive of emphysema. 3. Lingular subsegmental atelectasis or scarring.
```

id: `1290`  (real, Open-i)

```
FINDINGS: There is a 22 x 14 mm calcified nodule in the left lower lobe. A moderate hiatal hernia is present. Cardiomediastinal silhouette is normal. Pulmonary vasculature and XXXX are normal. No consolidation, pneumothorax or large pleural effusion. Osseous structures and soft tissues are normal. IMPRESSION: 1. No acute cardiopulmonary disease. 2. Calcified left paraesophageal versus intrapulmonary lymph node. 3. Moderate hiatus hernia.
```

id: `1739`  (real, Open-i)

```
FINDINGS: There is a cortical irregularity along the anterior margin of the sternum. In addition, there is a focal retrosternal hypodense convexity. The cardiac silhouette is within normal limits. The thoracic aorta is torturous however the mediastinal contours are within normal limits. There is no pneumothorax. There is no large pleural effusion. There is streaky XXXX opacity within the left lung base XXXX representing atelectasis. Otherwise, the lungs are clear. There is thoracic kyphosis. There is hyperinflation of the lungs. IMPRESSION: Core irregularity along the anterior margin of the sternum may represent an age-indeterminate nondisplaced fracture. In addition, focal lentiform hyperdensity along the XXXX aspect of the sternum may represent callus formation. Left basilar atelectasis otherwise clear lungs.
```

id: `1752`  (real, Open-i)

```
FINDINGS: Size is normal limits. Cardiomediastinal silhouette has normal contour. There is a vague opacity in the right infrahilar region. There is also a 5 mm well circumscribed nodule in the right upper lung XXXX. It is not well visualized on lateral view. IMPRESSION: 1. Right perihilar lung nodule. Recommend CT thorax with contrast to further assess. Dr. XXXX XXXX the findings XXXX.
```

## Number-dense (SYNTHETIC, not real patients)

id: `synth_000`  (SYNTHETIC)

```
FINDINGS: There is a 24 mm nodule in the right upper lobe, previously 6 mm. No pleural effusion. The heart measures 16 cm in transverse diameter. IMPRESSION: Right upper lobe nodule that is unlikely to represent a primary lung neoplasm. Recommend repeat imaging in 3 months.
```

id: `synth_001`  (SYNTHETIC)

```
FINDINGS: A 4.7 cm hepatic lesion is seen in the liver, measuring 74 Hounsfield units. The remaining liver is unremarkable. IMPRESSION: Hepatic lesion that may represent a simple cyst. No follow-up imaging is needed.
```

id: `synth_002`  (SYNTHETIC)

```
FINDINGS: Left ventricular ejection fraction is 26%. There is 30% narrowing of the proximal left anterior descending artery. IMPRESSION: Narrowing of the left anterior descending artery that may represent a hemodynamically significant stenosis. Recommend repeat imaging in 12 months.
```

id: `synth_003`  (SYNTHETIC)

```
FINDINGS: There is a 23 mm nodule in the left lower lobe, previously 3 mm. No pleural effusion. The heart measures 15 cm in transverse diameter. IMPRESSION: Left lower lobe nodule that cannot be excluded a metastasis. Recommend repeat imaging in 6 months.
```

## Negated-diagnosis wording (SYNTHETIC, not real patients)

id: `synth_000`  (SYNTHETIC)

```
FINDINGS: There is a 24 mm nodule in the right upper lobe, previously 6 mm. No pleural effusion. The heart measures 16 cm in transverse diameter. IMPRESSION: Right upper lobe nodule that is unlikely to represent a primary lung neoplasm. Recommend repeat imaging in 3 months.
```

id: `synth_010`  (SYNTHETIC)

```
FINDINGS: A 2.9 cm renal lesion is seen in the kidney, measuring 31 Hounsfield units. The remaining kidney is unremarkable. IMPRESSION: Renal lesion that is unlikely to represent an angiomyolipoma. Recommend follow-up CT in 12 months.
```
