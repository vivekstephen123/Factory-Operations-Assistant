"""
Generates the synthetic PDF manuals and documentation for the factory operations assistant.
Includes:
- M102_Manual.pdf
- M102_Maintenance_SOP.pdf
- Safety_Procedure.pdf
- Maintenance_History.pdf
"""

import os
import pymupdf

DOCS_DIR = os.path.dirname(__file__)


def create_pdf(filename: str, title: str, sections: list):
    filepath = os.path.join(DOCS_DIR, filename)
    doc = pymupdf.open()
    page = doc.new_page(width=595, height=842)

    y = 50
    page.insert_text((50, y), title, fontsize=16, fontname="helv", color=(0.1, 0.2, 0.5))
    y += 25
    page.draw_line(pymupdf.Point(50, y), pymupdf.Point(545, y), color=(0.7, 0.7, 0.7), width=1)
    y += 25

    for heading, paragraphs in sections:
        if y > 750:
            page = doc.new_page(width=595, height=842)
            y = 50
        page.insert_text((50, y), heading, fontsize=12, fontname="helv", color=(0.15, 0.3, 0.6))
        y += 18

        for p in paragraphs:
            words = p.split()
            line = ""
            for word in words:
                test_line = line + (" " if line else "") + word
                if len(test_line) > 78:
                    if y > 780:
                        page = doc.new_page(width=595, height=842)
                        y = 50
                    page.insert_text((50, y), line, fontsize=10, fontname="helv", color=(0.2, 0.2, 0.2))
                    y += 14
                    line = word
                else:
                    line = test_line
            if line:
                if y > 780:
                    page = doc.new_page(width=595, height=842)
                    y = 50
                page.insert_text((50, y), line, fontsize=10, fontname="helv", color=(0.2, 0.2, 0.2))
                y += 14
            y += 6

        y += 10

    doc.save(filepath)
    doc.close()
    print(f"Generated: {filename}")


def generate_all():
    os.makedirs(DOCS_DIR, exist_ok=True)

    # 1. M102_Manual.pdf
    create_pdf(
        "M102_Manual.pdf",
        "Technical Operations & User Manual - Machine M102 (5-Axis CNC Milling Center)",
        [
            (
                "1. Machine Specifications & Environmental Limits",
                [
                    "Machine Model: M102 High-Precision 5-Axis CNC Milling Center.",
                    "Spindle Power: 35 kW liquid-cooled high-speed spindle (up to 24,000 RPM).",
                    "Location: Bay 3 - Precision Machining Wing.",
                    "Operating Temperature Threshold: Normal operating temperature is between 20 deg C and 45 deg C. The thermal limit for the primary spindle and axis drives is 65 deg C.",
                ]
            ),
            (
                "2. Overheating Causes and Thermal Shutdown",
                [
                    "Overheating of Machine M102 is primarily caused by coolant circulation failure, blocked radiator heat-exchanger fins, coolant pump pressure drops below 2.5 bar, or prolonged heavy-load roughing passes without sufficient dwell time.",
                    "When spindle temperature exceeds 65 deg C, the internal thermal protection sensor triggers an automatic Emergency Thermal Shutdown (Fault Code E-704).",
                    "In the event of an overheating shutdown, operators must NOT force a reboot immediately. The machine must be allowed to cool down to 35 deg C, and the radiator coolant loop must be flushed and inspected for sediment or particulate blockages before re-engaging the spindle.",
                ]
            ),
            (
                "3. Cooling System Architecture",
                [
                    "The closed-loop cooling system uses a 50/50 mixture of demineralized water and ethylene glycol industrial coolant.",
                    "Coolant tank capacity is 60 Liters with an integrated inline filter rated at 25 microns.",
                ]
            )
        ]
    )

    # 2. M102_Maintenance_SOP.pdf
    create_pdf(
        "M102_Maintenance_SOP.pdf",
        "Standard Operating Procedure: Maintenance & Inspection Protocol for M102",
        [
            (
                "1. Inspection Schedules & Frequencies",
                [
                    "Daily Inspection: Check coolant fluid levels via sight gauge, monitor chip conveyor cleanliness, and verify pneumatic pressure (minimum 6.0 bar).",
                    "Weekly Inspection: Inspect way-lube oil reservoir, clean telescopic way-cover seals, and test emergency stop circuits.",
                    "The recommended cooling-system inspection interval is every 200 operational hours (or monthly, whichever occurs first). This inspection must verify radiator airflow, clean heat exchange coils, check pump impellers, and sample coolant pH levels (optimal 8.0 - 9.5).",
                ]
            ),
            (
                "2. Corrective Action for Cooling Failure & Overheating",
                [
                    "Step 1: Isolate power and tag-out Machine M102 per Lock-Out Tag-Out (LOTO) protocols.",
                    "Step 2: Inspect radiator intake filter mesh for metal chip shavings and dust buildup. Vacuum or clean with solvent.",
                    "Step 3: Check coolant pump flow rate. If flow rate is below 15 L/min at 3.0 bar, replace coolant filter element (Part No. FLT-M102-25).",
                    "Step 4: Execute a thermal calibration test run for 30 minutes at 6,000 RPM before resuming full production load.",
                ]
            ),
            (
                "3. Maintenance Request Protocol",
                [
                    "Whenever thermal shutdown occurs or cooling performance degrades, technicians must submit a High-Priority Maintenance Request immediately so that plant engineering can dispatch a specialized technician prior to resuming batch operations.",
                ]
            )
        ]
    )

    # 3. Safety_Procedure.pdf
    create_pdf(
        "Safety_Procedure.pdf",
        "Plant Safety Protocol & Emergency Response Standard",
        [
            (
                "1. Thermal and High-Voltage Hazards",
                [
                    "CNC machines and automated presses operate with high-voltage 415V 3-phase power and hydraulic circuits exceeding 180 bar.",
                    "Extreme heat hazard: When a machine experiences thermal shutdown, spindle and cooling jacket temperatures can exceed 80 deg C. Personnel must wear thermal-resistant PPE and allow 45 minutes natural cooling before opening enclosure panels.",
                ]
            ),
            (
                "2. Lock-Out / Tag-Out (LOTO) Requirement",
                [
                    "Before performing any mechanical inspection, filter replacement, or electrical servicing, technicians must apply padlocks and warning tags to the primary circuit breaker.",
                    "Never bypass interlock switches or coolant flow sensors during diagnosis.",
                ]
            )
        ]
    )

    # 4. Maintenance_History.pdf
    create_pdf(
        "Maintenance_History.pdf",
        "Equipment Maintenance Log & Historical Audit - Bay 3 CNC Centers",
        [
            (
                "1. Machine M102 Historical Summary",
                [
                    "Machine M102 was installed in Q1 2024. Over the past 6 months, M102 has maintained 94% uptime but experienced two significant downtime events in August 2026 totaling 31.5 hours.",
                    "Event 1 (August 12, 2026): 18.2 hours downtime due to cooling-system failure. Root cause was identified as heavy debris accumulation blocking the radiator cooling matrix, causing thermal shutdown E-704.",
                    "Event 2 (August 22, 2026): 13.3 hours downtime due to spindle optical sensor calibration drift after a vibration shock.",
                ]
            ),
            (
                "2. Preventative Action Recommendations",
                [
                    "Engineering recommended increasing the cooling system inspection frequency during summer months and installing secondary particulate mesh filters on M102 radiator intakes.",
                ]
            )
        ]
    )


if __name__ == "__main__":
    generate_all()
