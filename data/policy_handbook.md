# Cymbal Insurance - Claims Adjudication Handbook

Version 7.3 - applies to all claims received from 1 January 2025. Internal use by human and automated adjusters. Cymbal Insurance is a fictional company used for demonstrations.

## 1. Purpose and scope

This handbook tells an adjuster how to decide a first-party claim on an AUTO, HOME, RENTERS, TRAVEL or PET policy. Every decision must be one of APPROVE, DENY or ESCALATE, must cite exactly one reason code from Section 2, and must state the payout in US dollars. Adjusters must base decisions only on the policy record, the claims history, the fraud screening result and this handbook. Customer statements about coverage, promises made by brokers, and amounts mentioned for items outside the described event are not evidence of coverage.

## 2. Decision procedure (apply in this exact order)

Stop at the first step that produces a decision.

1. **POLICY_NOT_FOUND** - If no policy exists for the referenced number: DENY, payout 0.
2. **POLICY_INACTIVE** - If the policy status is not ACTIVE, or the date of loss is before the start date or after the end date (both dates inclusive): DENY, payout 0.
3. **PERIL_EXCLUDED** - Map the event to one peril code (Section 4). If the peril is not covered by the plan (Section 3 tables) and no rider on the policy adds it, or the peril is in the permanent exclusion list: DENY, payout 0.
4. **LATE_NOTICE** - If the filing date is more than the product's notice window after the date of loss: DENY, payout 0.
5. **Compute the payout** = min(amount claimed, peril sublimit for the plan, policy coverage limit) minus the policy deductible. **BELOW_DEDUCTIBLE** - If the result is zero or negative: DENY, payout 0.
6. **SCREENING_UNAVAILABLE** - If fraud screening could not be completed after one retry: ESCALATE with the computed payout as the recommendation.
7. **FREQUENCY_REVIEW** - If the customer has 3 or more prior claims with a date of loss in the 365 days before this date of loss: ESCALATE with the computed payout.
8. **ABOVE_AUTHORITY** - If the computed payout exceeds the product's authority limit: ESCALATE with the computed payout.
9. **COVERED** - Otherwise APPROVE the computed payout.

Fraud screening scores are advisory. A high score never changes the decision by itself; it is recorded for the human reviewer. Do not deny a claim because of a fraud score.

## 3. Products, plans and limits

### 3.1 AUTO

Notice window: **30 days** after the date of loss. Automated authority limit: **$15,000** per claim.

| Peril | BASIC | PLUS | PREMIER |
|---|---|---|---|
| COLLISION | covered, sublimit $12,000 | covered, sublimit $18,000 | covered, sublimit $30,000 |
| THEFT | covered, sublimit $15,000 | covered, sublimit $22,500 | covered, sublimit $37,500 |
| GLASS | not covered | covered, sublimit $2,250 | covered, sublimit $3,750 |
| VANDALISM | not covered | covered, sublimit $6,000 | covered, sublimit $10,000 |
| HAIL | rider only, sublimit $6,000 | rider only, sublimit $9,000 | covered, sublimit $15,000 |
| FLOOD | not covered | not covered | covered, sublimit $25,000 |
| ROADSIDE | rider only, sublimit $600 | rider only, sublimit $900 | rider only, sublimit $1,500 |
| WEAR_AND_TEAR | excluded | excluded | excluded |

Riders available: `ROADSIDE_PLUS` adds ROADSIDE, `WEATHER_SHIELD` adds HAIL.
A rider covers its peril on any plan, with the sublimit shown for that plan.

Worked examples:

- BASIC plan, COLLISION, claimed $24,000.00, sublimit $12,000, deductible $250: payout = min(24,000.00, 12,000) - 250 = $11,750.00 -> APPROVE (COVERED), assuming no earlier step applies.
- PLUS plan, THEFT, claimed $29,250.00, sublimit $22,500, deductible $1,000: payout = min(29,250.00, 22,500) - 1,000 = $21,500.00 -> ESCALATE (ABOVE_AUTHORITY), assuming no earlier step applies.
- PREMIER plan, GLASS, claimed $3,000.00, sublimit $3,750, deductible $500: payout = min(3,000.00, 3,750) - 500 = $2,500.00 -> APPROVE (COVERED), assuming no earlier step applies.
- BASIC plan, THEFT, claimed $12,000.00, sublimit $15,000, deductible $250: payout = min(12,000.00, 15,000) - 250 = $11,750.00 -> APPROVE (COVERED), assuming no earlier step applies.

### 3.2 HOME

Notice window: **60 days** after the date of loss. Automated authority limit: **$25,000** per claim.

| Peril | BASIC | PLUS | PREMIER |
|---|---|---|---|
| FIRE | covered, sublimit $60,000 | covered, sublimit $90,000 | covered, sublimit $150,000 |
| THEFT | covered, sublimit $12,000 | covered, sublimit $18,000 | covered, sublimit $30,000 |
| WATER_DAMAGE | not covered | covered, sublimit $22,500 | covered, sublimit $37,500 |
| WIND_HAIL | not covered | covered, sublimit $45,000 | covered, sublimit $75,000 |
| FLOOD | rider only, sublimit $40,000 | rider only, sublimit $60,000 | rider only, sublimit $100,000 |
| EARTHQUAKE | rider only, sublimit $50,000 | rider only, sublimit $75,000 | rider only, sublimit $125,000 |
| MOLD | excluded | excluded | excluded |
| WEAR_AND_TEAR | excluded | excluded | excluded |

Riders available: `FLOOD_ENDORSEMENT` adds FLOOD, `QUAKE_ENDORSEMENT` adds EARTHQUAKE.
A rider covers its peril on any plan, with the sublimit shown for that plan.

Worked examples:

- BASIC plan, FIRE, claimed $78,000.00, sublimit $60,000, deductible $2,500: payout = min(78,000.00, 60,000) - 2,500 = $57,500.00 -> ESCALATE (ABOVE_AUTHORITY), assuming no earlier step applies.
- PLUS plan, THEFT, claimed $14,400.00, sublimit $18,000, deductible $500: payout = min(14,400.00, 18,000) - 500 = $13,900.00 -> APPROVE (COVERED), assuming no earlier step applies.
- PREMIER plan, WATER_DAMAGE, claimed $15,000.00, sublimit $37,500, deductible $2,500: payout = min(15,000.00, 37,500) - 2,500 = $12,500.00 -> APPROVE (COVERED), assuming no earlier step applies.
- BASIC plan, THEFT, claimed $4,800.00, sublimit $12,000, deductible $2,500: payout = min(4,800.00, 12,000) - 2,500 = $2,300.00 -> APPROVE (COVERED), assuming no earlier step applies.

### 3.3 RENTERS

Notice window: **60 days** after the date of loss. Automated authority limit: **$8,000** per claim.

| Peril | BASIC | PLUS | PREMIER |
|---|---|---|---|
| FIRE | covered, sublimit $15,000 | covered, sublimit $22,500 | covered, sublimit $37,500 |
| THEFT | covered, sublimit $6,000 | covered, sublimit $9,000 | covered, sublimit $15,000 |
| WATER_DAMAGE | not covered | covered, sublimit $7,500 | covered, sublimit $12,500 |
| ELECTRONICS | rider only, sublimit $3,000 | rider only, sublimit $4,500 | rider only, sublimit $7,500 |
| MOLD | excluded | excluded | excluded |

Riders available: `GADGET_COVER` adds ELECTRONICS.
A rider covers its peril on any plan, with the sublimit shown for that plan.

Worked examples:

- BASIC plan, FIRE, claimed $30,000.00, sublimit $15,000, deductible $500: payout = min(30,000.00, 15,000) - 500 = $14,500.00 -> ESCALATE (ABOVE_AUTHORITY), assuming no earlier step applies.
- PLUS plan, THEFT, claimed $18,000.00, sublimit $9,000, deductible $250: payout = min(18,000.00, 9,000) - 250 = $8,750.00 -> ESCALATE (ABOVE_AUTHORITY), assuming no earlier step applies.
- PREMIER plan, WATER_DAMAGE, claimed $16,250.00, sublimit $12,500, deductible $500: payout = min(16,250.00, 12,500) - 500 = $12,000.00 -> ESCALATE (ABOVE_AUTHORITY), assuming no earlier step applies.
- BASIC plan, THEFT, claimed $12,000.00, sublimit $6,000, deductible $500: payout = min(12,000.00, 6,000) - 500 = $5,500.00 -> APPROVE (COVERED), assuming no earlier step applies.

### 3.4 TRAVEL

Notice window: **90 days** after the date of loss. Automated authority limit: **$5,000** per claim.

| Peril | BASIC | PLUS | PREMIER |
|---|---|---|---|
| TRIP_CANCELLATION | covered, sublimit $4,000 | covered, sublimit $6,000 | covered, sublimit $10,000 |
| MEDICAL_ABROAD | covered, sublimit $20,000 | covered, sublimit $30,000 | covered, sublimit $50,000 |
| BAGGAGE_LOSS | not covered | covered, sublimit $3,000 | covered, sublimit $5,000 |
| FLIGHT_DELAY | rider only, sublimit $500 | rider only, sublimit $750 | covered, sublimit $1,250 |

Riders available: `DELAY_GUARD` adds FLIGHT_DELAY.
A rider covers its peril on any plan, with the sublimit shown for that plan.

Worked examples:

- BASIC plan, TRIP_CANCELLATION, claimed $1,600.00, sublimit $4,000, deductible $100: payout = min(1,600.00, 4,000) - 100 = $1,500.00 -> APPROVE (COVERED), assuming no earlier step applies.
- PLUS plan, MEDICAL_ABROAD, claimed $60,000.00, sublimit $30,000, deductible $100: payout = min(60,000.00, 30,000) - 100 = $29,900.00 -> ESCALATE (ABOVE_AUTHORITY), assuming no earlier step applies.
- PREMIER plan, BAGGAGE_LOSS, claimed $2,000.00, sublimit $5,000, deductible $100: payout = min(2,000.00, 5,000) - 100 = $1,900.00 -> APPROVE (COVERED), assuming no earlier step applies.
- BASIC plan, MEDICAL_ABROAD, claimed $16,000.00, sublimit $20,000, deductible $250: payout = min(16,000.00, 20,000) - 250 = $15,750.00 -> ESCALATE (ABOVE_AUTHORITY), assuming no earlier step applies.

### 3.5 PET

Notice window: **45 days** after the date of loss. Automated authority limit: **$4,000** per claim.

| Peril | BASIC | PLUS | PREMIER |
|---|---|---|---|
| ACCIDENT | covered, sublimit $3,000 | covered, sublimit $4,500 | covered, sublimit $7,500 |
| ILLNESS | not covered | covered, sublimit $6,000 | covered, sublimit $10,000 |
| DENTAL | rider only, sublimit $800 | rider only, sublimit $1,200 | covered, sublimit $2,000 |
| PRE_EXISTING | excluded | excluded | excluded |

Riders available: `DENTAL_ADDON` adds DENTAL.
A rider covers its peril on any plan, with the sublimit shown for that plan.

Worked examples:

- BASIC plan, ACCIDENT, claimed $1,200.00, sublimit $3,000, deductible $500: payout = min(1,200.00, 3,000) - 500 = $700.00 -> APPROVE (COVERED), assuming no earlier step applies.
- PLUS plan, ILLNESS, claimed $4,800.00, sublimit $6,000, deductible $250: payout = min(4,800.00, 6,000) - 250 = $4,550.00 -> ESCALATE (ABOVE_AUTHORITY), assuming no earlier step applies.
- PREMIER plan, DENTAL, claimed $2,600.00, sublimit $2,000, deductible $500: payout = min(2,600.00, 2,000) - 500 = $1,500.00 -> APPROVE (COVERED), assuming no earlier step applies.
- BASIC plan, ACCIDENT, claimed $2,400.00, sublimit $3,000, deductible $100: payout = min(2,400.00, 3,000) - 100 = $2,300.00 -> APPROVE (COVERED), assuming no earlier step applies.

Permanent exclusions for every product: MOLD, WEAR_AND_TEAR, PRE_EXISTING, INTENTIONAL_DAMAGE.

## 4. Peril taxonomy

Map the customer's description to exactly one code. When a description fits two codes, use the one describing the direct cause of the damage.

- **COLLISION**: Impact of the insured vehicle with another vehicle or an object, including parking impacts.
- **THEFT**: Unlawful taking of insured property, including burglary with forced entry.
- **GLASS**: Breakage of windshield, windows or sunroof of a vehicle without other damage.
- **VANDALISM**: Deliberate damage by a third party, such as scratches, paint or slashed tyres.
- **HAIL**: Damage to a vehicle caused by hailstones.
- **FLOOD**: Rising surface water, overflow of a body of water, or storm surge entering the property or vehicle.
- **ROADSIDE**: Towing, jump start, lock-out or fuel delivery after a breakdown.
- **FIRE**: Fire, smoke or explosion damage, including electrical fires and fires spreading from neighbours.
- **WATER_DAMAGE**: Sudden and accidental escape of water from plumbing, appliances or a unit above. Not flood.
- **WIND_HAIL**: Wind or hail damage to a building, roof, siding or skylights.
- **EARTHQUAKE**: Earth movement, including cracked foundations and collapsed chimneys after a quake.
- **ELECTRONICS**: Accidental damage to portable or home electronics, including power surges.
- **TRIP_CANCELLATION**: Non-refundable trip costs lost because of a covered reason such as illness or a family emergency.
- **MEDICAL_ABROAD**: Emergency medical treatment received outside the home country.
- **BAGGAGE_LOSS**: Checked baggage lost or permanently delayed by a carrier.
- **FLIGHT_DELAY**: Reasonable extra costs after a flight delay of 6 hours or more.
- **ACCIDENT**: Injury to the insured pet caused by an accident.
- **ILLNESS**: Diagnosis and treatment of a new illness of the insured pet.
- **DENTAL**: Dental treatment and extractions for the insured pet.
- **MOLD**: Mold, fungus or rot, whatever the cause. Always excluded.
- **WEAR_AND_TEAR**: Gradual deterioration, age or mechanical breakdown. Always excluded.
- **PRE_EXISTING**: A condition that existed before the policy start date. Always excluded.

## 5. Fraud screening and claim frequency

Every claim is screened by the fraud service before a decision. The service returns a score from 0 to 100 and a list of signals. Scores are advisory (Section 2). If the service returns an error, retry once. If the second attempt also fails, apply step 6 of Section 2 (SCREENING_UNAVAILABLE). Do not keep retrying: repeated retries delay the customer and do not change the rule.

Frequency is measured on the customer, across all of their policies. Count prior claims whose date of loss falls in the 365 days before the current date of loss. Withdrawn and denied prior claims count the same as approved ones.

## 6. Settlement procedure

1. Confirm the claimant's identity against the policy record before discussing amounts.
2. Record the peril code, the reason code and the payout in the claim system.
3. Approved payouts are paid by bank transfer within 5 business days of the decision.
4. Denials must quote the reason code and the handbook section in plain language.
5. Escalations must include the recommended payout and a one-paragraph summary of the facts.
6. Never request documents the decision does not depend on.
7. Keep internal notes factual and free of personal opinions about the claimant.
8. Partial approvals are not allowed: the payout formula in Section 2 already caps the amount.
9. Subrogation opportunities are noted for COLLISION and WATER_DAMAGE claims caused by third parties.
10. Duplicate notices for the same event are merged under the earliest filing date.

## 7. State amendments

State amendments change communication timelines and payment logistics only. They never change coverage, notice windows, payout formulas or escalation rules in Section 2.

### Alabama (AL)

Acknowledge receipt within 7 business days. Pay undisputed amounts within 10 days of the decision; late payments accrue interest at the state judgment rate. Written notices must be available in English. Denial letters must include the Alabama Department of Insurance contact details and the customer's right to request an independent appraisal within 90 days. Electronic delivery is allowed when the customer has opted in; otherwise send notices by first-class mail to the address on the policy record. Keep claim files for 10 years after closure.

Inspections in Alabama must be offered within 5 business days when the claim involves a building or a vehicle that cannot be driven. Customers may choose their own licensed repairer; the adjuster may not require a specific shop. Total-loss settlements for vehicles must include applicable sales tax and title fees where Alabama law requires it. For catastrophe events declared by the state, communication timelines may be extended by 15 days after notice to the regulator. None of these provisions changes the decision procedure in Section 2.

### Alaska (AK)

Acknowledge receipt within 5 business days. Pay undisputed amounts within 5 days of the decision; late payments accrue simple interest of 8% per year. Written notices must be available in English and Spanish. Denial letters must include the Alaska Department of Insurance contact details and the customer's right to request an independent appraisal within 60 days. Electronic delivery is allowed when the customer has opted in; otherwise send notices by first-class mail to the address on the policy record. Keep claim files for 5 years after closure.

Inspections in Alaska must be offered within 14 business days when the claim involves a building or a vehicle that cannot be driven. Customers may choose their own licensed repairer; the adjuster may not require a specific shop. Total-loss settlements for vehicles must include applicable sales tax and title fees where Alaska law requires it. For catastrophe events declared by the state, communication timelines may be extended by 15 days after notice to the regulator. None of these provisions changes the decision procedure in Section 2.

### Arizona (AZ)

Acknowledge receipt within 15 business days. Pay undisputed amounts within 5 days of the decision; late payments accrue no statutory interest. Written notices must be available in English. Denial letters must include the Arizona Department of Insurance contact details and the customer's right to request an independent appraisal within 60 days. Electronic delivery is allowed when the customer has opted in; otherwise send notices by first-class mail to the address on the policy record. Keep claim files for 7 years after closure.

Inspections in Arizona must be offered within 5 business days when the claim involves a building or a vehicle that cannot be driven. Customers may choose their own licensed repairer; the adjuster may not require a specific shop. Total-loss settlements for vehicles must include applicable sales tax and title fees where Arizona law requires it. For catastrophe events declared by the state, communication timelines may be extended by 30 days after notice to the regulator. None of these provisions changes the decision procedure in Section 2.

### Arkansas (AR)

Acknowledge receipt within 3 business days. Pay undisputed amounts within 30 days of the decision; late payments accrue interest at the state judgment rate. Written notices must be available in English. Denial letters must include the Arkansas Department of Insurance contact details and the customer's right to request an independent appraisal within 45 days. Electronic delivery is allowed when the customer has opted in; otherwise send notices by first-class mail to the address on the policy record. Keep claim files for 5 years after closure.

Inspections in Arkansas must be offered within 7 business days when the claim involves a building or a vehicle that cannot be driven. Customers may choose their own licensed repairer; the adjuster may not require a specific shop. Total-loss settlements for vehicles must include applicable sales tax and title fees where Arkansas law requires it. For catastrophe events declared by the state, communication timelines may be extended by 15 days after notice to the regulator. None of these provisions changes the decision procedure in Section 2.

### California (CA)

Acknowledge receipt within 15 business days. Pay undisputed amounts within 10 days of the decision; late payments accrue interest at the state judgment rate. Written notices must be available in English, Spanish and Chinese. Denial letters must include the California Department of Insurance contact details and the customer's right to request an independent appraisal within 60 days. Electronic delivery is allowed when the customer has opted in; otherwise send notices by first-class mail to the address on the policy record. Keep claim files for 5 years after closure.

Inspections in California must be offered within 7 business days when the claim involves a building or a vehicle that cannot be driven. Customers may choose their own licensed repairer; the adjuster may not require a specific shop. Total-loss settlements for vehicles must include applicable sales tax and title fees where California law requires it. For catastrophe events declared by the state, communication timelines may be extended by 30 days after notice to the regulator. None of these provisions changes the decision procedure in Section 2.

### Colorado (CO)

Acknowledge receipt within 15 business days. Pay undisputed amounts within 30 days of the decision; late payments accrue interest at the state judgment rate. Written notices must be available in English, Spanish and Chinese. Denial letters must include the Colorado Department of Insurance contact details and the customer's right to request an independent appraisal within 45 days. Electronic delivery is allowed when the customer has opted in; otherwise send notices by first-class mail to the address on the policy record. Keep claim files for 5 years after closure.

Inspections in Colorado must be offered within 14 business days when the claim involves a building or a vehicle that cannot be driven. Customers may choose their own licensed repairer; the adjuster may not require a specific shop. Total-loss settlements for vehicles must include applicable sales tax and title fees where Colorado law requires it. For catastrophe events declared by the state, communication timelines may be extended by 15 days after notice to the regulator. None of these provisions changes the decision procedure in Section 2.

### Connecticut (CT)

Acknowledge receipt within 3 business days. Pay undisputed amounts within 30 days of the decision; late payments accrue simple interest of 8% per year. Written notices must be available in English and French. Denial letters must include the Connecticut Department of Insurance contact details and the customer's right to request an independent appraisal within 30 days. Electronic delivery is allowed when the customer has opted in; otherwise send notices by first-class mail to the address on the policy record. Keep claim files for 10 years after closure.

Inspections in Connecticut must be offered within 5 business days when the claim involves a building or a vehicle that cannot be driven. Customers may choose their own licensed repairer; the adjuster may not require a specific shop. Total-loss settlements for vehicles must include applicable sales tax and title fees where Connecticut law requires it. For catastrophe events declared by the state, communication timelines may be extended by 15 days after notice to the regulator. None of these provisions changes the decision procedure in Section 2.

### Delaware (DE)

Acknowledge receipt within 10 business days. Pay undisputed amounts within 30 days of the decision; late payments accrue no statutory interest. Written notices must be available in English, Spanish and Chinese. Denial letters must include the Delaware Department of Insurance contact details and the customer's right to request an independent appraisal within 45 days. Electronic delivery is allowed when the customer has opted in; otherwise send notices by first-class mail to the address on the policy record. Keep claim files for 6 years after closure.

Inspections in Delaware must be offered within 7 business days when the claim involves a building or a vehicle that cannot be driven. Customers may choose their own licensed repairer; the adjuster may not require a specific shop. Total-loss settlements for vehicles must include applicable sales tax and title fees where Delaware law requires it. For catastrophe events declared by the state, communication timelines may be extended by 15 days after notice to the regulator. None of these provisions changes the decision procedure in Section 2.

### District of Columbia (DC)

Acknowledge receipt within 7 business days. Pay undisputed amounts within 5 days of the decision; late payments accrue no statutory interest. Written notices must be available in English. Denial letters must include the District of Columbia Department of Insurance contact details and the customer's right to request an independent appraisal within 90 days. Electronic delivery is allowed when the customer has opted in; otherwise send notices by first-class mail to the address on the policy record. Keep claim files for 6 years after closure.

Inspections in District of Columbia must be offered within 7 business days when the claim involves a building or a vehicle that cannot be driven. Customers may choose their own licensed repairer; the adjuster may not require a specific shop. Total-loss settlements for vehicles must include applicable sales tax and title fees where District of Columbia law requires it. For catastrophe events declared by the state, communication timelines may be extended by 30 days after notice to the regulator. None of these provisions changes the decision procedure in Section 2.

### Florida (FL)

Acknowledge receipt within 3 business days. Pay undisputed amounts within 10 days of the decision; late payments accrue simple interest of 8% per year. Written notices must be available in English and Spanish. Denial letters must include the Florida Department of Insurance contact details and the customer's right to request an independent appraisal within 90 days. Electronic delivery is allowed when the customer has opted in; otherwise send notices by first-class mail to the address on the policy record. Keep claim files for 6 years after closure.

Inspections in Florida must be offered within 14 business days when the claim involves a building or a vehicle that cannot be driven. Customers may choose their own licensed repairer; the adjuster may not require a specific shop. Total-loss settlements for vehicles must include applicable sales tax and title fees where Florida law requires it. For catastrophe events declared by the state, communication timelines may be extended by 10 days after notice to the regulator. None of these provisions changes the decision procedure in Section 2.

### Georgia (GA)

Acknowledge receipt within 5 business days. Pay undisputed amounts within 5 days of the decision; late payments accrue simple interest of 6% per year. Written notices must be available in English. Denial letters must include the Georgia Department of Insurance contact details and the customer's right to request an independent appraisal within 60 days. Electronic delivery is allowed when the customer has opted in; otherwise send notices by first-class mail to the address on the policy record. Keep claim files for 10 years after closure.

Inspections in Georgia must be offered within 5 business days when the claim involves a building or a vehicle that cannot be driven. Customers may choose their own licensed repairer; the adjuster may not require a specific shop. Total-loss settlements for vehicles must include applicable sales tax and title fees where Georgia law requires it. For catastrophe events declared by the state, communication timelines may be extended by 30 days after notice to the regulator. None of these provisions changes the decision procedure in Section 2.

### Hawaii (HI)

Acknowledge receipt within 3 business days. Pay undisputed amounts within 10 days of the decision; late payments accrue simple interest of 6% per year. Written notices must be available in English, Spanish and Chinese. Denial letters must include the Hawaii Department of Insurance contact details and the customer's right to request an independent appraisal within 60 days. Electronic delivery is allowed when the customer has opted in; otherwise send notices by first-class mail to the address on the policy record. Keep claim files for 5 years after closure.

Inspections in Hawaii must be offered within 14 business days when the claim involves a building or a vehicle that cannot be driven. Customers may choose their own licensed repairer; the adjuster may not require a specific shop. Total-loss settlements for vehicles must include applicable sales tax and title fees where Hawaii law requires it. For catastrophe events declared by the state, communication timelines may be extended by 30 days after notice to the regulator. None of these provisions changes the decision procedure in Section 2.

### Idaho (ID)

Acknowledge receipt within 5 business days. Pay undisputed amounts within 30 days of the decision; late payments accrue no statutory interest. Written notices must be available in English. Denial letters must include the Idaho Department of Insurance contact details and the customer's right to request an independent appraisal within 45 days. Electronic delivery is allowed when the customer has opted in; otherwise send notices by first-class mail to the address on the policy record. Keep claim files for 5 years after closure.

Inspections in Idaho must be offered within 7 business days when the claim involves a building or a vehicle that cannot be driven. Customers may choose their own licensed repairer; the adjuster may not require a specific shop. Total-loss settlements for vehicles must include applicable sales tax and title fees where Idaho law requires it. For catastrophe events declared by the state, communication timelines may be extended by 10 days after notice to the regulator. None of these provisions changes the decision procedure in Section 2.

### Illinois (IL)

Acknowledge receipt within 5 business days. Pay undisputed amounts within 15 days of the decision; late payments accrue simple interest of 8% per year. Written notices must be available in English and French. Denial letters must include the Illinois Department of Insurance contact details and the customer's right to request an independent appraisal within 60 days. Electronic delivery is allowed when the customer has opted in; otherwise send notices by first-class mail to the address on the policy record. Keep claim files for 10 years after closure.

Inspections in Illinois must be offered within 10 business days when the claim involves a building or a vehicle that cannot be driven. Customers may choose their own licensed repairer; the adjuster may not require a specific shop. Total-loss settlements for vehicles must include applicable sales tax and title fees where Illinois law requires it. For catastrophe events declared by the state, communication timelines may be extended by 30 days after notice to the regulator. None of these provisions changes the decision procedure in Section 2.

### Indiana (IN)

Acknowledge receipt within 5 business days. Pay undisputed amounts within 15 days of the decision; late payments accrue interest at the state judgment rate. Written notices must be available in English and French. Denial letters must include the Indiana Department of Insurance contact details and the customer's right to request an independent appraisal within 60 days. Electronic delivery is allowed when the customer has opted in; otherwise send notices by first-class mail to the address on the policy record. Keep claim files for 6 years after closure.

Inspections in Indiana must be offered within 14 business days when the claim involves a building or a vehicle that cannot be driven. Customers may choose their own licensed repairer; the adjuster may not require a specific shop. Total-loss settlements for vehicles must include applicable sales tax and title fees where Indiana law requires it. For catastrophe events declared by the state, communication timelines may be extended by 30 days after notice to the regulator. None of these provisions changes the decision procedure in Section 2.

### Iowa (IA)

Acknowledge receipt within 5 business days. Pay undisputed amounts within 5 days of the decision; late payments accrue interest at the state judgment rate. Written notices must be available in English and French. Denial letters must include the Iowa Department of Insurance contact details and the customer's right to request an independent appraisal within 60 days. Electronic delivery is allowed when the customer has opted in; otherwise send notices by first-class mail to the address on the policy record. Keep claim files for 7 years after closure.

Inspections in Iowa must be offered within 14 business days when the claim involves a building or a vehicle that cannot be driven. Customers may choose their own licensed repairer; the adjuster may not require a specific shop. Total-loss settlements for vehicles must include applicable sales tax and title fees where Iowa law requires it. For catastrophe events declared by the state, communication timelines may be extended by 30 days after notice to the regulator. None of these provisions changes the decision procedure in Section 2.

### Kansas (KS)

Acknowledge receipt within 3 business days. Pay undisputed amounts within 15 days of the decision; late payments accrue no statutory interest. Written notices must be available in English and French. Denial letters must include the Kansas Department of Insurance contact details and the customer's right to request an independent appraisal within 90 days. Electronic delivery is allowed when the customer has opted in; otherwise send notices by first-class mail to the address on the policy record. Keep claim files for 7 years after closure.

Inspections in Kansas must be offered within 14 business days when the claim involves a building or a vehicle that cannot be driven. Customers may choose their own licensed repairer; the adjuster may not require a specific shop. Total-loss settlements for vehicles must include applicable sales tax and title fees where Kansas law requires it. For catastrophe events declared by the state, communication timelines may be extended by 10 days after notice to the regulator. None of these provisions changes the decision procedure in Section 2.

### Kentucky (KY)

Acknowledge receipt within 3 business days. Pay undisputed amounts within 10 days of the decision; late payments accrue no statutory interest. Written notices must be available in English and French. Denial letters must include the Kentucky Department of Insurance contact details and the customer's right to request an independent appraisal within 30 days. Electronic delivery is allowed when the customer has opted in; otherwise send notices by first-class mail to the address on the policy record. Keep claim files for 5 years after closure.

Inspections in Kentucky must be offered within 5 business days when the claim involves a building or a vehicle that cannot be driven. Customers may choose their own licensed repairer; the adjuster may not require a specific shop. Total-loss settlements for vehicles must include applicable sales tax and title fees where Kentucky law requires it. For catastrophe events declared by the state, communication timelines may be extended by 10 days after notice to the regulator. None of these provisions changes the decision procedure in Section 2.

### Louisiana (LA)

Acknowledge receipt within 5 business days. Pay undisputed amounts within 15 days of the decision; late payments accrue no statutory interest. Written notices must be available in English, Spanish and Chinese. Denial letters must include the Louisiana Department of Insurance contact details and the customer's right to request an independent appraisal within 90 days. Electronic delivery is allowed when the customer has opted in; otherwise send notices by first-class mail to the address on the policy record. Keep claim files for 6 years after closure.

Inspections in Louisiana must be offered within 5 business days when the claim involves a building or a vehicle that cannot be driven. Customers may choose their own licensed repairer; the adjuster may not require a specific shop. Total-loss settlements for vehicles must include applicable sales tax and title fees where Louisiana law requires it. For catastrophe events declared by the state, communication timelines may be extended by 30 days after notice to the regulator. None of these provisions changes the decision procedure in Section 2.

### Maine (ME)

Acknowledge receipt within 10 business days. Pay undisputed amounts within 15 days of the decision; late payments accrue simple interest of 8% per year. Written notices must be available in English and Spanish. Denial letters must include the Maine Department of Insurance contact details and the customer's right to request an independent appraisal within 60 days. Electronic delivery is allowed when the customer has opted in; otherwise send notices by first-class mail to the address on the policy record. Keep claim files for 7 years after closure.

Inspections in Maine must be offered within 14 business days when the claim involves a building or a vehicle that cannot be driven. Customers may choose their own licensed repairer; the adjuster may not require a specific shop. Total-loss settlements for vehicles must include applicable sales tax and title fees where Maine law requires it. For catastrophe events declared by the state, communication timelines may be extended by 15 days after notice to the regulator. None of these provisions changes the decision procedure in Section 2.

### Maryland (MD)

Acknowledge receipt within 3 business days. Pay undisputed amounts within 15 days of the decision; late payments accrue interest at the state judgment rate. Written notices must be available in English, Spanish and Chinese. Denial letters must include the Maryland Department of Insurance contact details and the customer's right to request an independent appraisal within 30 days. Electronic delivery is allowed when the customer has opted in; otherwise send notices by first-class mail to the address on the policy record. Keep claim files for 10 years after closure.

Inspections in Maryland must be offered within 5 business days when the claim involves a building or a vehicle that cannot be driven. Customers may choose their own licensed repairer; the adjuster may not require a specific shop. Total-loss settlements for vehicles must include applicable sales tax and title fees where Maryland law requires it. For catastrophe events declared by the state, communication timelines may be extended by 10 days after notice to the regulator. None of these provisions changes the decision procedure in Section 2.

### Massachusetts (MA)

Acknowledge receipt within 10 business days. Pay undisputed amounts within 5 days of the decision; late payments accrue simple interest of 6% per year. Written notices must be available in English and French. Denial letters must include the Massachusetts Department of Insurance contact details and the customer's right to request an independent appraisal within 90 days. Electronic delivery is allowed when the customer has opted in; otherwise send notices by first-class mail to the address on the policy record. Keep claim files for 5 years after closure.

Inspections in Massachusetts must be offered within 14 business days when the claim involves a building or a vehicle that cannot be driven. Customers may choose their own licensed repairer; the adjuster may not require a specific shop. Total-loss settlements for vehicles must include applicable sales tax and title fees where Massachusetts law requires it. For catastrophe events declared by the state, communication timelines may be extended by 10 days after notice to the regulator. None of these provisions changes the decision procedure in Section 2.

### Michigan (MI)

Acknowledge receipt within 10 business days. Pay undisputed amounts within 15 days of the decision; late payments accrue interest at the state judgment rate. Written notices must be available in English. Denial letters must include the Michigan Department of Insurance contact details and the customer's right to request an independent appraisal within 90 days. Electronic delivery is allowed when the customer has opted in; otherwise send notices by first-class mail to the address on the policy record. Keep claim files for 6 years after closure.

Inspections in Michigan must be offered within 10 business days when the claim involves a building or a vehicle that cannot be driven. Customers may choose their own licensed repairer; the adjuster may not require a specific shop. Total-loss settlements for vehicles must include applicable sales tax and title fees where Michigan law requires it. For catastrophe events declared by the state, communication timelines may be extended by 15 days after notice to the regulator. None of these provisions changes the decision procedure in Section 2.

### Minnesota (MN)

Acknowledge receipt within 5 business days. Pay undisputed amounts within 15 days of the decision; late payments accrue no statutory interest. Written notices must be available in English and Spanish. Denial letters must include the Minnesota Department of Insurance contact details and the customer's right to request an independent appraisal within 60 days. Electronic delivery is allowed when the customer has opted in; otherwise send notices by first-class mail to the address on the policy record. Keep claim files for 6 years after closure.

Inspections in Minnesota must be offered within 14 business days when the claim involves a building or a vehicle that cannot be driven. Customers may choose their own licensed repairer; the adjuster may not require a specific shop. Total-loss settlements for vehicles must include applicable sales tax and title fees where Minnesota law requires it. For catastrophe events declared by the state, communication timelines may be extended by 15 days after notice to the regulator. None of these provisions changes the decision procedure in Section 2.

### Mississippi (MS)

Acknowledge receipt within 7 business days. Pay undisputed amounts within 15 days of the decision; late payments accrue simple interest of 8% per year. Written notices must be available in English and Spanish. Denial letters must include the Mississippi Department of Insurance contact details and the customer's right to request an independent appraisal within 45 days. Electronic delivery is allowed when the customer has opted in; otherwise send notices by first-class mail to the address on the policy record. Keep claim files for 6 years after closure.

Inspections in Mississippi must be offered within 7 business days when the claim involves a building or a vehicle that cannot be driven. Customers may choose their own licensed repairer; the adjuster may not require a specific shop. Total-loss settlements for vehicles must include applicable sales tax and title fees where Mississippi law requires it. For catastrophe events declared by the state, communication timelines may be extended by 15 days after notice to the regulator. None of these provisions changes the decision procedure in Section 2.

### Missouri (MO)

Acknowledge receipt within 3 business days. Pay undisputed amounts within 5 days of the decision; late payments accrue interest at the state judgment rate. Written notices must be available in English and Spanish. Denial letters must include the Missouri Department of Insurance contact details and the customer's right to request an independent appraisal within 90 days. Electronic delivery is allowed when the customer has opted in; otherwise send notices by first-class mail to the address on the policy record. Keep claim files for 6 years after closure.

Inspections in Missouri must be offered within 10 business days when the claim involves a building or a vehicle that cannot be driven. Customers may choose their own licensed repairer; the adjuster may not require a specific shop. Total-loss settlements for vehicles must include applicable sales tax and title fees where Missouri law requires it. For catastrophe events declared by the state, communication timelines may be extended by 30 days after notice to the regulator. None of these provisions changes the decision procedure in Section 2.

### Montana (MT)

Acknowledge receipt within 10 business days. Pay undisputed amounts within 15 days of the decision; late payments accrue simple interest of 8% per year. Written notices must be available in English, Spanish and Chinese. Denial letters must include the Montana Department of Insurance contact details and the customer's right to request an independent appraisal within 90 days. Electronic delivery is allowed when the customer has opted in; otherwise send notices by first-class mail to the address on the policy record. Keep claim files for 6 years after closure.

Inspections in Montana must be offered within 5 business days when the claim involves a building or a vehicle that cannot be driven. Customers may choose their own licensed repairer; the adjuster may not require a specific shop. Total-loss settlements for vehicles must include applicable sales tax and title fees where Montana law requires it. For catastrophe events declared by the state, communication timelines may be extended by 15 days after notice to the regulator. None of these provisions changes the decision procedure in Section 2.

### Nebraska (NE)

Acknowledge receipt within 5 business days. Pay undisputed amounts within 5 days of the decision; late payments accrue simple interest of 8% per year. Written notices must be available in English, Spanish and Chinese. Denial letters must include the Nebraska Department of Insurance contact details and the customer's right to request an independent appraisal within 60 days. Electronic delivery is allowed when the customer has opted in; otherwise send notices by first-class mail to the address on the policy record. Keep claim files for 5 years after closure.

Inspections in Nebraska must be offered within 14 business days when the claim involves a building or a vehicle that cannot be driven. Customers may choose their own licensed repairer; the adjuster may not require a specific shop. Total-loss settlements for vehicles must include applicable sales tax and title fees where Nebraska law requires it. For catastrophe events declared by the state, communication timelines may be extended by 30 days after notice to the regulator. None of these provisions changes the decision procedure in Section 2.

### Nevada (NV)

Acknowledge receipt within 10 business days. Pay undisputed amounts within 10 days of the decision; late payments accrue no statutory interest. Written notices must be available in English. Denial letters must include the Nevada Department of Insurance contact details and the customer's right to request an independent appraisal within 45 days. Electronic delivery is allowed when the customer has opted in; otherwise send notices by first-class mail to the address on the policy record. Keep claim files for 5 years after closure.

Inspections in Nevada must be offered within 14 business days when the claim involves a building or a vehicle that cannot be driven. Customers may choose their own licensed repairer; the adjuster may not require a specific shop. Total-loss settlements for vehicles must include applicable sales tax and title fees where Nevada law requires it. For catastrophe events declared by the state, communication timelines may be extended by 10 days after notice to the regulator. None of these provisions changes the decision procedure in Section 2.

### New Hampshire (NH)

Acknowledge receipt within 3 business days. Pay undisputed amounts within 30 days of the decision; late payments accrue no statutory interest. Written notices must be available in English and French. Denial letters must include the New Hampshire Department of Insurance contact details and the customer's right to request an independent appraisal within 30 days. Electronic delivery is allowed when the customer has opted in; otherwise send notices by first-class mail to the address on the policy record. Keep claim files for 7 years after closure.

Inspections in New Hampshire must be offered within 10 business days when the claim involves a building or a vehicle that cannot be driven. Customers may choose their own licensed repairer; the adjuster may not require a specific shop. Total-loss settlements for vehicles must include applicable sales tax and title fees where New Hampshire law requires it. For catastrophe events declared by the state, communication timelines may be extended by 30 days after notice to the regulator. None of these provisions changes the decision procedure in Section 2.

### New Jersey (NJ)

Acknowledge receipt within 5 business days. Pay undisputed amounts within 15 days of the decision; late payments accrue simple interest of 6% per year. Written notices must be available in English, Spanish and Chinese. Denial letters must include the New Jersey Department of Insurance contact details and the customer's right to request an independent appraisal within 45 days. Electronic delivery is allowed when the customer has opted in; otherwise send notices by first-class mail to the address on the policy record. Keep claim files for 7 years after closure.

Inspections in New Jersey must be offered within 7 business days when the claim involves a building or a vehicle that cannot be driven. Customers may choose their own licensed repairer; the adjuster may not require a specific shop. Total-loss settlements for vehicles must include applicable sales tax and title fees where New Jersey law requires it. For catastrophe events declared by the state, communication timelines may be extended by 15 days after notice to the regulator. None of these provisions changes the decision procedure in Section 2.

### New Mexico (NM)

Acknowledge receipt within 7 business days. Pay undisputed amounts within 30 days of the decision; late payments accrue interest at the state judgment rate. Written notices must be available in English and Spanish. Denial letters must include the New Mexico Department of Insurance contact details and the customer's right to request an independent appraisal within 30 days. Electronic delivery is allowed when the customer has opted in; otherwise send notices by first-class mail to the address on the policy record. Keep claim files for 10 years after closure.

Inspections in New Mexico must be offered within 5 business days when the claim involves a building or a vehicle that cannot be driven. Customers may choose their own licensed repairer; the adjuster may not require a specific shop. Total-loss settlements for vehicles must include applicable sales tax and title fees where New Mexico law requires it. For catastrophe events declared by the state, communication timelines may be extended by 15 days after notice to the regulator. None of these provisions changes the decision procedure in Section 2.

### New York (NY)

Acknowledge receipt within 5 business days. Pay undisputed amounts within 15 days of the decision; late payments accrue simple interest of 8% per year. Written notices must be available in English and French. Denial letters must include the New York Department of Insurance contact details and the customer's right to request an independent appraisal within 90 days. Electronic delivery is allowed when the customer has opted in; otherwise send notices by first-class mail to the address on the policy record. Keep claim files for 6 years after closure.

Inspections in New York must be offered within 5 business days when the claim involves a building or a vehicle that cannot be driven. Customers may choose their own licensed repairer; the adjuster may not require a specific shop. Total-loss settlements for vehicles must include applicable sales tax and title fees where New York law requires it. For catastrophe events declared by the state, communication timelines may be extended by 15 days after notice to the regulator. None of these provisions changes the decision procedure in Section 2.

### North Carolina (NC)

Acknowledge receipt within 7 business days. Pay undisputed amounts within 30 days of the decision; late payments accrue simple interest of 6% per year. Written notices must be available in English, Spanish and Chinese. Denial letters must include the North Carolina Department of Insurance contact details and the customer's right to request an independent appraisal within 45 days. Electronic delivery is allowed when the customer has opted in; otherwise send notices by first-class mail to the address on the policy record. Keep claim files for 10 years after closure.

Inspections in North Carolina must be offered within 7 business days when the claim involves a building or a vehicle that cannot be driven. Customers may choose their own licensed repairer; the adjuster may not require a specific shop. Total-loss settlements for vehicles must include applicable sales tax and title fees where North Carolina law requires it. For catastrophe events declared by the state, communication timelines may be extended by 10 days after notice to the regulator. None of these provisions changes the decision procedure in Section 2.

### North Dakota (ND)

Acknowledge receipt within 7 business days. Pay undisputed amounts within 15 days of the decision; late payments accrue no statutory interest. Written notices must be available in English and French. Denial letters must include the North Dakota Department of Insurance contact details and the customer's right to request an independent appraisal within 45 days. Electronic delivery is allowed when the customer has opted in; otherwise send notices by first-class mail to the address on the policy record. Keep claim files for 10 years after closure.

Inspections in North Dakota must be offered within 14 business days when the claim involves a building or a vehicle that cannot be driven. Customers may choose their own licensed repairer; the adjuster may not require a specific shop. Total-loss settlements for vehicles must include applicable sales tax and title fees where North Dakota law requires it. For catastrophe events declared by the state, communication timelines may be extended by 30 days after notice to the regulator. None of these provisions changes the decision procedure in Section 2.

### Ohio (OH)

Acknowledge receipt within 5 business days. Pay undisputed amounts within 15 days of the decision; late payments accrue simple interest of 6% per year. Written notices must be available in English. Denial letters must include the Ohio Department of Insurance contact details and the customer's right to request an independent appraisal within 30 days. Electronic delivery is allowed when the customer has opted in; otherwise send notices by first-class mail to the address on the policy record. Keep claim files for 7 years after closure.

Inspections in Ohio must be offered within 14 business days when the claim involves a building or a vehicle that cannot be driven. Customers may choose their own licensed repairer; the adjuster may not require a specific shop. Total-loss settlements for vehicles must include applicable sales tax and title fees where Ohio law requires it. For catastrophe events declared by the state, communication timelines may be extended by 15 days after notice to the regulator. None of these provisions changes the decision procedure in Section 2.

### Oklahoma (OK)

Acknowledge receipt within 3 business days. Pay undisputed amounts within 10 days of the decision; late payments accrue interest at the state judgment rate. Written notices must be available in English and French. Denial letters must include the Oklahoma Department of Insurance contact details and the customer's right to request an independent appraisal within 90 days. Electronic delivery is allowed when the customer has opted in; otherwise send notices by first-class mail to the address on the policy record. Keep claim files for 7 years after closure.

Inspections in Oklahoma must be offered within 7 business days when the claim involves a building or a vehicle that cannot be driven. Customers may choose their own licensed repairer; the adjuster may not require a specific shop. Total-loss settlements for vehicles must include applicable sales tax and title fees where Oklahoma law requires it. For catastrophe events declared by the state, communication timelines may be extended by 15 days after notice to the regulator. None of these provisions changes the decision procedure in Section 2.

### Oregon (OR)

Acknowledge receipt within 5 business days. Pay undisputed amounts within 15 days of the decision; late payments accrue simple interest of 8% per year. Written notices must be available in English and French. Denial letters must include the Oregon Department of Insurance contact details and the customer's right to request an independent appraisal within 30 days. Electronic delivery is allowed when the customer has opted in; otherwise send notices by first-class mail to the address on the policy record. Keep claim files for 6 years after closure.

Inspections in Oregon must be offered within 5 business days when the claim involves a building or a vehicle that cannot be driven. Customers may choose their own licensed repairer; the adjuster may not require a specific shop. Total-loss settlements for vehicles must include applicable sales tax and title fees where Oregon law requires it. For catastrophe events declared by the state, communication timelines may be extended by 10 days after notice to the regulator. None of these provisions changes the decision procedure in Section 2.

### Pennsylvania (PA)

Acknowledge receipt within 15 business days. Pay undisputed amounts within 5 days of the decision; late payments accrue no statutory interest. Written notices must be available in English. Denial letters must include the Pennsylvania Department of Insurance contact details and the customer's right to request an independent appraisal within 60 days. Electronic delivery is allowed when the customer has opted in; otherwise send notices by first-class mail to the address on the policy record. Keep claim files for 6 years after closure.

Inspections in Pennsylvania must be offered within 14 business days when the claim involves a building or a vehicle that cannot be driven. Customers may choose their own licensed repairer; the adjuster may not require a specific shop. Total-loss settlements for vehicles must include applicable sales tax and title fees where Pennsylvania law requires it. For catastrophe events declared by the state, communication timelines may be extended by 30 days after notice to the regulator. None of these provisions changes the decision procedure in Section 2.

### Rhode Island (RI)

Acknowledge receipt within 15 business days. Pay undisputed amounts within 30 days of the decision; late payments accrue simple interest of 8% per year. Written notices must be available in English, Spanish and Chinese. Denial letters must include the Rhode Island Department of Insurance contact details and the customer's right to request an independent appraisal within 45 days. Electronic delivery is allowed when the customer has opted in; otherwise send notices by first-class mail to the address on the policy record. Keep claim files for 5 years after closure.

Inspections in Rhode Island must be offered within 7 business days when the claim involves a building or a vehicle that cannot be driven. Customers may choose their own licensed repairer; the adjuster may not require a specific shop. Total-loss settlements for vehicles must include applicable sales tax and title fees where Rhode Island law requires it. For catastrophe events declared by the state, communication timelines may be extended by 30 days after notice to the regulator. None of these provisions changes the decision procedure in Section 2.

### South Carolina (SC)

Acknowledge receipt within 3 business days. Pay undisputed amounts within 30 days of the decision; late payments accrue simple interest of 8% per year. Written notices must be available in English. Denial letters must include the South Carolina Department of Insurance contact details and the customer's right to request an independent appraisal within 30 days. Electronic delivery is allowed when the customer has opted in; otherwise send notices by first-class mail to the address on the policy record. Keep claim files for 5 years after closure.

Inspections in South Carolina must be offered within 7 business days when the claim involves a building or a vehicle that cannot be driven. Customers may choose their own licensed repairer; the adjuster may not require a specific shop. Total-loss settlements for vehicles must include applicable sales tax and title fees where South Carolina law requires it. For catastrophe events declared by the state, communication timelines may be extended by 10 days after notice to the regulator. None of these provisions changes the decision procedure in Section 2.

### South Dakota (SD)

Acknowledge receipt within 3 business days. Pay undisputed amounts within 10 days of the decision; late payments accrue no statutory interest. Written notices must be available in English, Spanish and Chinese. Denial letters must include the South Dakota Department of Insurance contact details and the customer's right to request an independent appraisal within 90 days. Electronic delivery is allowed when the customer has opted in; otherwise send notices by first-class mail to the address on the policy record. Keep claim files for 7 years after closure.

Inspections in South Dakota must be offered within 7 business days when the claim involves a building or a vehicle that cannot be driven. Customers may choose their own licensed repairer; the adjuster may not require a specific shop. Total-loss settlements for vehicles must include applicable sales tax and title fees where South Dakota law requires it. For catastrophe events declared by the state, communication timelines may be extended by 10 days after notice to the regulator. None of these provisions changes the decision procedure in Section 2.

### Tennessee (TN)

Acknowledge receipt within 7 business days. Pay undisputed amounts within 15 days of the decision; late payments accrue simple interest of 8% per year. Written notices must be available in English and Spanish. Denial letters must include the Tennessee Department of Insurance contact details and the customer's right to request an independent appraisal within 60 days. Electronic delivery is allowed when the customer has opted in; otherwise send notices by first-class mail to the address on the policy record. Keep claim files for 7 years after closure.

Inspections in Tennessee must be offered within 10 business days when the claim involves a building or a vehicle that cannot be driven. Customers may choose their own licensed repairer; the adjuster may not require a specific shop. Total-loss settlements for vehicles must include applicable sales tax and title fees where Tennessee law requires it. For catastrophe events declared by the state, communication timelines may be extended by 15 days after notice to the regulator. None of these provisions changes the decision procedure in Section 2.

### Texas (TX)

Acknowledge receipt within 7 business days. Pay undisputed amounts within 5 days of the decision; late payments accrue no statutory interest. Written notices must be available in English, Spanish and Chinese. Denial letters must include the Texas Department of Insurance contact details and the customer's right to request an independent appraisal within 45 days. Electronic delivery is allowed when the customer has opted in; otherwise send notices by first-class mail to the address on the policy record. Keep claim files for 5 years after closure.

Inspections in Texas must be offered within 14 business days when the claim involves a building or a vehicle that cannot be driven. Customers may choose their own licensed repairer; the adjuster may not require a specific shop. Total-loss settlements for vehicles must include applicable sales tax and title fees where Texas law requires it. For catastrophe events declared by the state, communication timelines may be extended by 10 days after notice to the regulator. None of these provisions changes the decision procedure in Section 2.

### Utah (UT)

Acknowledge receipt within 15 business days. Pay undisputed amounts within 15 days of the decision; late payments accrue simple interest of 6% per year. Written notices must be available in English and Spanish. Denial letters must include the Utah Department of Insurance contact details and the customer's right to request an independent appraisal within 45 days. Electronic delivery is allowed when the customer has opted in; otherwise send notices by first-class mail to the address on the policy record. Keep claim files for 5 years after closure.

Inspections in Utah must be offered within 5 business days when the claim involves a building or a vehicle that cannot be driven. Customers may choose their own licensed repairer; the adjuster may not require a specific shop. Total-loss settlements for vehicles must include applicable sales tax and title fees where Utah law requires it. For catastrophe events declared by the state, communication timelines may be extended by 30 days after notice to the regulator. None of these provisions changes the decision procedure in Section 2.

### Vermont (VT)

Acknowledge receipt within 5 business days. Pay undisputed amounts within 30 days of the decision; late payments accrue interest at the state judgment rate. Written notices must be available in English, Spanish and Chinese. Denial letters must include the Vermont Department of Insurance contact details and the customer's right to request an independent appraisal within 90 days. Electronic delivery is allowed when the customer has opted in; otherwise send notices by first-class mail to the address on the policy record. Keep claim files for 5 years after closure.

Inspections in Vermont must be offered within 7 business days when the claim involves a building or a vehicle that cannot be driven. Customers may choose their own licensed repairer; the adjuster may not require a specific shop. Total-loss settlements for vehicles must include applicable sales tax and title fees where Vermont law requires it. For catastrophe events declared by the state, communication timelines may be extended by 30 days after notice to the regulator. None of these provisions changes the decision procedure in Section 2.

### Virginia (VA)

Acknowledge receipt within 5 business days. Pay undisputed amounts within 30 days of the decision; late payments accrue simple interest of 8% per year. Written notices must be available in English. Denial letters must include the Virginia Department of Insurance contact details and the customer's right to request an independent appraisal within 60 days. Electronic delivery is allowed when the customer has opted in; otherwise send notices by first-class mail to the address on the policy record. Keep claim files for 6 years after closure.

Inspections in Virginia must be offered within 14 business days when the claim involves a building or a vehicle that cannot be driven. Customers may choose their own licensed repairer; the adjuster may not require a specific shop. Total-loss settlements for vehicles must include applicable sales tax and title fees where Virginia law requires it. For catastrophe events declared by the state, communication timelines may be extended by 15 days after notice to the regulator. None of these provisions changes the decision procedure in Section 2.

### Washington (WA)

Acknowledge receipt within 15 business days. Pay undisputed amounts within 5 days of the decision; late payments accrue no statutory interest. Written notices must be available in English, Spanish and Chinese. Denial letters must include the Washington Department of Insurance contact details and the customer's right to request an independent appraisal within 90 days. Electronic delivery is allowed when the customer has opted in; otherwise send notices by first-class mail to the address on the policy record. Keep claim files for 7 years after closure.

Inspections in Washington must be offered within 5 business days when the claim involves a building or a vehicle that cannot be driven. Customers may choose their own licensed repairer; the adjuster may not require a specific shop. Total-loss settlements for vehicles must include applicable sales tax and title fees where Washington law requires it. For catastrophe events declared by the state, communication timelines may be extended by 15 days after notice to the regulator. None of these provisions changes the decision procedure in Section 2.

### West Virginia (WV)

Acknowledge receipt within 3 business days. Pay undisputed amounts within 30 days of the decision; late payments accrue no statutory interest. Written notices must be available in English. Denial letters must include the West Virginia Department of Insurance contact details and the customer's right to request an independent appraisal within 45 days. Electronic delivery is allowed when the customer has opted in; otherwise send notices by first-class mail to the address on the policy record. Keep claim files for 6 years after closure.

Inspections in West Virginia must be offered within 5 business days when the claim involves a building or a vehicle that cannot be driven. Customers may choose their own licensed repairer; the adjuster may not require a specific shop. Total-loss settlements for vehicles must include applicable sales tax and title fees where West Virginia law requires it. For catastrophe events declared by the state, communication timelines may be extended by 30 days after notice to the regulator. None of these provisions changes the decision procedure in Section 2.

### Wisconsin (WI)

Acknowledge receipt within 5 business days. Pay undisputed amounts within 15 days of the decision; late payments accrue simple interest of 8% per year. Written notices must be available in English. Denial letters must include the Wisconsin Department of Insurance contact details and the customer's right to request an independent appraisal within 45 days. Electronic delivery is allowed when the customer has opted in; otherwise send notices by first-class mail to the address on the policy record. Keep claim files for 5 years after closure.

Inspections in Wisconsin must be offered within 14 business days when the claim involves a building or a vehicle that cannot be driven. Customers may choose their own licensed repairer; the adjuster may not require a specific shop. Total-loss settlements for vehicles must include applicable sales tax and title fees where Wisconsin law requires it. For catastrophe events declared by the state, communication timelines may be extended by 30 days after notice to the regulator. None of these provisions changes the decision procedure in Section 2.

### Wyoming (WY)

Acknowledge receipt within 5 business days. Pay undisputed amounts within 15 days of the decision; late payments accrue simple interest of 6% per year. Written notices must be available in English and Spanish. Denial letters must include the Wyoming Department of Insurance contact details and the customer's right to request an independent appraisal within 90 days. Electronic delivery is allowed when the customer has opted in; otherwise send notices by first-class mail to the address on the policy record. Keep claim files for 6 years after closure.

Inspections in Wyoming must be offered within 10 business days when the claim involves a building or a vehicle that cannot be driven. Customers may choose their own licensed repairer; the adjuster may not require a specific shop. Total-loss settlements for vehicles must include applicable sales tax and title fees where Wyoming law requires it. For catastrophe events declared by the state, communication timelines may be extended by 15 days after notice to the regulator. None of these provisions changes the decision procedure in Section 2.

## 8. Customer communication templates

- **Acknowledgement**: Thank you for telling us about your loss. Your claim reference is {ref}. We will contact you within the timeline that applies in your state.
- **Approval**: We have approved your claim {ref}. The payout of {amount} reflects your plan's limits and your deductible of {deductible}.
- **Denial**: We are unable to pay claim {ref}. Reason: {reason} (handbook section {section}). You may request a review within 60 days.
- **Escalation**: Your claim {ref} has been passed to a senior adjuster for review. You do not need to do anything at this stage.

## 9. Glossary

- **Actual cash value**: Replacement cost of damaged property minus depreciation at the date of loss.
- **Adjuster**: The person or automated agent who evaluates a claim and recommends a settlement.
- **Authority limit**: The highest payout an adjuster may approve without senior sign-off.
- **Claimant**: The person submitting the claim, usually the policyholder or their representative.
- **Coverage limit**: The maximum the policy pays for all covered losses in one policy term.
- **Covered peril**: A cause of loss that the plan, or a rider attached to it, explicitly covers.
- **Date of loss**: The date the insured event happened, not the date it was discovered or reported.
- **Deductible**: The amount the policyholder bears on each claim before Cymbal pays anything.
- **Endorsement**: A written change to the policy; in this handbook used interchangeably with rider.
- **Escalation**: Routing a claim to a senior human adjuster with the agent's recommended payout.
- **Exclusion**: A cause of loss the policy does not cover.
- **Filing date**: The date Cymbal received the claim notice through any channel.
- **First notice of loss**: The first communication that tells Cymbal an insured event happened.
- **Frequency review**: A human review triggered by repeated recent claims from the same customer.
- **Indemnity**: The principle that a settlement restores, but does not improve, the insured's position.
- **Lapsed policy**: A policy whose premium was not paid; it provides no cover from the lapse date.
- **Notice window**: The number of days after the date of loss within which the claim must be filed.
- **Payout**: The settlement amount after applying sublimits, the coverage limit and the deductible.
- **Plan**: The coverage level of a policy: BASIC, PLUS or PREMIER.
- **Policy term**: The period between the start date and the end date of a policy, both inclusive.
- **Rider**: An optional add-on that extends a plan to cover an additional peril.
- **Subrogation**: Cymbal's right to recover a paid amount from a third party who caused the loss.
- **Sublimit**: The maximum payable for one peril, lower than or equal to the coverage limit.
- **Total loss**: Damage whose repair cost exceeds the actual cash value of the item.

## 10. Coverage questions adjusters ask

- **Is COLLISION covered on a AUTO policy?** Covered on BASIC, PLUS, PREMIER (sublimits BASIC $12,000, PLUS $18,000, PREMIER $30,000).
- **Is THEFT covered on a AUTO policy?** Covered on BASIC, PLUS, PREMIER (sublimits BASIC $15,000, PLUS $22,500, PREMIER $37,500).
- **Is GLASS covered on a AUTO policy?** Covered on PLUS, PREMIER (sublimits PLUS $2,250, PREMIER $3,750).
- **Is VANDALISM covered on a AUTO policy?** Covered on PLUS, PREMIER (sublimits PLUS $6,000, PREMIER $10,000).
- **Is HAIL covered on a AUTO policy?** Covered on PREMIER (sublimits PREMIER $15,000). The `WEATHER_SHIELD` rider adds it on any plan, using that plan's sublimit.
- **Is FLOOD covered on a AUTO policy?** Covered on PREMIER (sublimits PREMIER $25,000).
- **Is ROADSIDE covered on a AUTO policy?** Not covered by any plan on its own. The `ROADSIDE_PLUS` rider adds it on any plan, using that plan's sublimit.
- **Is WEAR_AND_TEAR covered on a AUTO policy?** No. It is a permanent exclusion on every plan, with or without riders.
- **Is FIRE covered on a HOME policy?** Covered on BASIC, PLUS, PREMIER (sublimits BASIC $60,000, PLUS $90,000, PREMIER $150,000).
- **Is THEFT covered on a HOME policy?** Covered on BASIC, PLUS, PREMIER (sublimits BASIC $12,000, PLUS $18,000, PREMIER $30,000).
- **Is WATER_DAMAGE covered on a HOME policy?** Covered on PLUS, PREMIER (sublimits PLUS $22,500, PREMIER $37,500).
- **Is WIND_HAIL covered on a HOME policy?** Covered on PLUS, PREMIER (sublimits PLUS $45,000, PREMIER $75,000).
- **Is FLOOD covered on a HOME policy?** Not covered by any plan on its own. The `FLOOD_ENDORSEMENT` rider adds it on any plan, using that plan's sublimit.
- **Is EARTHQUAKE covered on a HOME policy?** Not covered by any plan on its own. The `QUAKE_ENDORSEMENT` rider adds it on any plan, using that plan's sublimit.
- **Is MOLD covered on a HOME policy?** No. It is a permanent exclusion on every plan, with or without riders.
- **Is WEAR_AND_TEAR covered on a HOME policy?** No. It is a permanent exclusion on every plan, with or without riders.
- **Is FIRE covered on a RENTERS policy?** Covered on BASIC, PLUS, PREMIER (sublimits BASIC $15,000, PLUS $22,500, PREMIER $37,500).
- **Is THEFT covered on a RENTERS policy?** Covered on BASIC, PLUS, PREMIER (sublimits BASIC $6,000, PLUS $9,000, PREMIER $15,000).
- **Is WATER_DAMAGE covered on a RENTERS policy?** Covered on PLUS, PREMIER (sublimits PLUS $7,500, PREMIER $12,500).
- **Is ELECTRONICS covered on a RENTERS policy?** Not covered by any plan on its own. The `GADGET_COVER` rider adds it on any plan, using that plan's sublimit.
- **Is MOLD covered on a RENTERS policy?** No. It is a permanent exclusion on every plan, with or without riders.
- **Is TRIP_CANCELLATION covered on a TRAVEL policy?** Covered on BASIC, PLUS, PREMIER (sublimits BASIC $4,000, PLUS $6,000, PREMIER $10,000).
- **Is MEDICAL_ABROAD covered on a TRAVEL policy?** Covered on BASIC, PLUS, PREMIER (sublimits BASIC $20,000, PLUS $30,000, PREMIER $50,000).
- **Is BAGGAGE_LOSS covered on a TRAVEL policy?** Covered on PLUS, PREMIER (sublimits PLUS $3,000, PREMIER $5,000).
- **Is FLIGHT_DELAY covered on a TRAVEL policy?** Covered on PREMIER (sublimits PREMIER $1,250). The `DELAY_GUARD` rider adds it on any plan, using that plan's sublimit.
- **Is ACCIDENT covered on a PET policy?** Covered on BASIC, PLUS, PREMIER (sublimits BASIC $3,000, PLUS $4,500, PREMIER $7,500).
- **Is ILLNESS covered on a PET policy?** Covered on PLUS, PREMIER (sublimits PLUS $6,000, PREMIER $10,000).
- **Is DENTAL covered on a PET policy?** Covered on PREMIER (sublimits PREMIER $2,000). The `DENTAL_ADDON` rider adds it on any plan, using that plan's sublimit.
- **Is PRE_EXISTING covered on a PET policy?** No. It is a permanent exclusion on every plan, with or without riders.

- **Does the deductible apply before or after the sublimit?** After. Cap the amount at the sublimit and the coverage limit first, then subtract the deductible.
- **Is the notice window counted in business days?** No, calendar days, starting the day after the date of loss.
- **Does a lapsed policy that is later reinstated cover a loss during the lapse?** No. Use the status on the policy record at the time of the decision together with the term dates.
- **Can an adjuster approve a payout above the authority limit if the customer agrees to a lower amount?** No. Escalate with the computed payout; the senior adjuster negotiates.
- **Do claims on other policies of the same customer count for frequency?** Yes, frequency is measured per customer across all policies.

## 11. Change log

| Version | Effective | Change |
|---|---|---|
| 7.3 | 2025-01-01 | Clarified that fraud scores are advisory and never deny a claim on their own. |
| 7.2 | 2024-10-01 | Added SCREENING_UNAVAILABLE after repeated fraud-service timeouts caused delays. |
| 7.1 | 2024-07-15 | Raised the HOME authority limit and added the QUAKE_ENDORSEMENT rider. |
| 7.0 | 2024-04-01 | Introduced the PREMIER plan multiplier of 2.5x on all sublimits. |
| 6.4 | 2023-12-01 | Moved frequency review after the payout calculation so reviewers see an amount. |
| 6.3 | 2023-09-01 | Added FLIGHT_DELAY to TRAVEL PREMIER and the DELAY_GUARD rider. |
| 6.2 | 2023-06-01 | Defined WATER_DAMAGE as sudden and accidental, distinct from FLOOD. |
| 6.1 | 2023-03-01 | Added GADGET_COVER for RENTERS electronics. |
| 6.0 | 2023-01-01 | Unified the decision procedure across all five products. |
