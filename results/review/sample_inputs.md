# Sample inputs for the demo (paste into the box)

Real reports come from the public Open-i chest X-ray collection. Reports marked SYNTHETIC were written by our generator and are not real patients.

## Normal chest (nothing to explain)
id: `10`

```
FINDINGS: The cardiomediastinal silhouette is within normal limits for size and contour. The lungs are normally inflated without evidence of focal airspace disease, pleural effusion, or pneumothorax. Stable calcified granuloma within the right upper lung. No acute bone abnormality.. IMPRESSION: No acute cardiopulmonary process.
```

## Uncertainty: 'cannot be excluded' / 'possible'
id: `2522`

```
FINDINGS: Normal heart size and mediastinal contours. No focal airspace consolidation. Chronic appearing left greater than right lung base scarring with possible small effusions. No pneumothorax. Visualized osseous structures are unremarkable in appearance. IMPRESSION: 1. Chronic appearing bibasilar pleural abnormality with possible small effusions. 2. No evidence of pneumonia. TIPS shunt visualized. .
```

## Uncertainty: 'may represent'
id: `126`

```
FINDINGS: Vague increased opacity which appears to be within the left lower lobe. Question of this could be developing or resolving pneumonia. Lungs are otherwise clear. No pleural effusions or pneumothoraces. heart and mediastinum are stable normal size heart. Atherosclerotic vascular disease. Degenerative changes in the thoracic spine. IMPRESSION: Vague opacity at the left lung base which appears to be within the left lower lobe. This may represent resolving or developing pneumonia given the patient's history.
```

## Left / right matters
id: `1040`

```
FINDINGS:  IMPRESSION: Heart size is normal. Mediastinal width is within normal limits for supine AP technique. No edema. No focal infiltrate. No pleural effusion or pneumothorax. Right hilar and right lung base calcifications are compatible with old granulomatous disease. There is a very mild anterior wedge deformity of a midthoracic vertebrae, possibly T7, age-indeterminate. Correlate for midthoracic tenderness. No displaced, acute rib fractures are identified.
```

## Has a measurement (real report)
id: `1339`

```
FINDINGS: Small 3.3 mm right-sided pneumothorax only visible on the left lateral decubitus film. Left lung is clear. Normal cardiac contour. No evidence of pleural effusion. IMPRESSION: 1. Small 3.3 mm right-sided pneumothorax.
```

## SYNTHETIC: numbers + hedge + follow-up (made-up report)
id: `synth_000`

```
FINDINGS: There is a 24 mm nodule in the right upper lobe, previously 6 mm. No pleural effusion. The heart measures 16 cm in transverse diameter. IMPRESSION: Right upper lobe nodule that is unlikely to represent a primary lung neoplasm. Recommend repeat imaging in 3 months.
```

## SYNTHETIC: organ lesion with size (made-up report)
id: `synth_001`

```
FINDINGS: A 4.7 cm hepatic lesion is seen in the liver, measuring 74 Hounsfield units. The remaining liver is unremarkable. IMPRESSION: Hepatic lesion that may represent a simple cyst. No follow-up imaging is needed.
```
