# Component inventory

Personal inventory of parts on hand. Off-topic from the product-discovery work in `docs/`, kept here for convenience.

Add a row when something arrives, update `qty` when something leaves. Add new category sections as needed.

## MCUs

| Part                                  | Qty | Description                             | Datasheet                                                               | Octopart                                                  | Source | Notes                                |
| ------------------------------------- | --- | --------------------------------------- | ----------------------------------------------------------------------- | --------------------------------------------------------- | ------ | ------------------------------------ |
| [PIC12F675](parts/pic12f675.md)       | 1   | 8-bit PIC MCU, 8-pin, 1 K flash, ADC    | [DS41190F](https://ww1.microchip.com/downloads/en/DeviceDoc/41190F.pdf) | [search](https://octopart.com/search?q=PIC12F675)         | manual |                                      |
| [PIC16F628-20I/P](parts/pic16f628.md) | 2   | 8-bit PIC MCU, 18-pin, original (pre-A) | [DS40300C](https://ww1.microchip.com/downloads/en/DeviceDoc/40300c.pdf) | [search](https://octopart.com/search?q=PIC16F628-20I%2FP) | manual | Shares page with PIC16F628A (family) |
| [PIC16F628A](parts/pic16f628.md)      | 2   | 8-bit PIC MCU, 18-pin, 2 K flash, USART | [DS40044G](https://ww1.microchip.com/downloads/en/DeviceDoc/40044G.pdf) | [search](https://octopart.com/search?q=PIC16F628A)        | manual |                                      |

## ICs

| Part                          | Qty | Description                                 | Datasheet                                                                       | Octopart                                           | Source | Notes                                           |
| ----------------------------- | --- | ------------------------------------------- | ------------------------------------------------------------------------------- | -------------------------------------------------- | ------ | ----------------------------------------------- |
| 74HC165N                      | 5   | 8-bit shift register (PISO)                 | [SN74HC165](https://www.ti.com/lit/ds/symlink/sn74hc165.pdf)                    | [search](https://octopart.com/search?q=74HC165N)   | manual |                                                 |
| 74HC595N                      | 5   | 8-bit shift register (SIPO)                 | [SN74HC595](https://www.ti.com/lit/ds/symlink/sn74hc595.pdf)                    | [search](https://octopart.com/search?q=74HC595N)   | manual |                                                 |
| [7660S](parts/7660s.md)       | 2   | Charge-pump voltage converter               | [ICL7660S](https://www.renesas.com/en/document/dst/icl7660s-icl7660a-datasheet) | [search](https://octopart.com/search?q=ICL7660S)   | manual |                                                 |
| CD4013BE                      | 3   | Dual D-type flip-flop (CMOS 4000)           | [CD4013B](https://www.ti.com/lit/ds/symlink/cd4013b.pdf)                        | [search](https://octopart.com/search?q=CD4013BE)   | manual |                                                 |
| HCF4019BE                     | 5   | Quad AND/OR select gate (CMOS 4000)         | [CD4019B](https://www.ti.com/lit/ds/symlink/cd4019b.pdf)                        | [search](https://octopart.com/search?q=HCF4019BE)  | manual | Generic 4019 (TI); ST-specific not found        |
| HEF4011BP                     | 1   | Quad 2-input NAND gate (CMOS 4000)          | [HEF4011B](https://assets.nexperia.com/documents/data-sheet/HEF4011B.pdf)       | [search](https://octopart.com/search?q=HEF4011BP)  | manual |                                                 |
| HEF4078BP                     | 2   | 8-input NOR/OR gate (CMOS 4000)             | [CD4078B](https://www.ti.com/lit/ds/symlink/cd4078b.pdf)                        | [search](https://octopart.com/search?q=HEF4078BP)  | manual | Generic 4078 (TI); NXP-specific not found       |
| LM358N                        | 1   | Dual op-amp, single-supply                  | [LM358](https://www.ti.com/lit/ds/symlink/lm358.pdf)                            | [search](https://octopart.com/search?q=LM358N)     | manual |                                                 |
| LM555CM                       | 4   | Precision timer (mono/astable)              | [LM555](https://www.ti.com/lit/ds/symlink/lm555.pdf)                            | [search](https://octopart.com/search?q=LM555CM)    | manual | National-lineage 555; equiv. to NE555N/P        |
| LM6132                        | 2   | Dual rail-to-rail op-amp, 10 MHz            | [LM6132](https://www.ti.com/lit/ds/symlink/lm6132.pdf)                          | [search](https://octopart.com/search?q=LM6132)     | manual |                                                 |
| LTV847                        | 1   | Quad optocoupler, 5 kV isolation            | [LTV-847](https://www.jameco.com/Jameco/Products/ProdDS/878286.pdf)             | [search](https://octopart.com/search?q=LTV847)     | manual |                                                 |
| MCP4922                       | 2   | Dual 12-bit DAC, SPI                        | [DS22250A](https://ww1.microchip.com/downloads/en/devicedoc/22250a.pdf)         | [search](https://octopart.com/search?q=MCP4922)    | manual |                                                 |
| NE555N                        | 3   | Precision timer (mono/astable)              | [NE555](https://www.ti.com/lit/ds/symlink/ne555.pdf)                            | [search](https://octopart.com/search?q=NE555N)     | manual | Signetics-lineage bipolar 555 (DIP, "N" suffix) |
| NE555P                        | 2   | Precision timer (mono/astable)              | [NE555](https://www.ti.com/lit/ds/symlink/ne555.pdf)                            | [search](https://octopart.com/search?q=NE555P)     | manual | Marking variant of NE555N (same chip)           |
| SN7414SN                      | 3   | Hex Schmitt-trigger inverter (TTL)          | [SN7414](https://www.ti.com/lit/ds/symlink/sn74ls14.pdf)                        | [search](https://octopart.com/search?q=SN7414)     | manual | Unusual extra 'SN' suffix in marking            |
| TC4018BP                      | 1   | Presettable divide-by-N counter (CMOS 4000) | [CD4018B](https://www.ti.com/lit/ds/symlink/cd4018b.pdf)                        | [search](https://octopart.com/search?q=TC4018BP)   | manual | Generic 4018 (TI); Toshiba-specific not found   |
| [TL082CF](parts/tl082.md)     | 3   | Dual JFET-input op-amp                      | [TL082](https://www.ti.com/lit/ds/symlink/tl082.pdf)                            | [search](https://octopart.com/search?q=TL082CF)    | manual |                                                 |
| [TL082CP](parts/tl082.md)     | 2   | Dual JFET-input op-amp                      | [TL082](https://www.ti.com/lit/ds/symlink/tl082.pdf)                            | [search](https://octopart.com/search?q=TL082CP)    | manual | Marking variant of TL082CF (same chip)          |
| [TL084IN](parts/tl084.md)     | 2   | Quad JFET-input op-amp                      | [TL084](https://www.ti.com/lit/ds/symlink/tl084.pdf)                            | [search](https://octopart.com/search?q=TL084IN)    | manual |                                                 |
| TLC548CP                      | 1   | 8-bit serial-output ADC, 4 MHz I/O          | [TLC548](https://www.ti.com/product/TLC548)                                     | [search](https://octopart.com/search?q=TLC548CP)   | manual | TI product page (PDF link from there)           |
| TLCS549                       | 1   | 8-bit serial-output ADC, 1.1 MHz I/O        | [TLC549](https://www.ti.com/product/TLC549)                                     | [search](https://octopart.com/search?q=TLC549)     | manual | Slower sibling of TLC548; extra S in marking    |
| U74HC14L                      | 2   | Hex Schmitt-trigger inverter                | [SN74HC14](https://www.ti.com/lit/ds/symlink/sn74hc14.pdf)                      | [search](https://octopart.com/search?q=74HC14)     | manual | UTC 74HC14 clone                                |
| ULN2803APG                    | 1   | 8-ch Darlington sink driver, 500 mA, 50 V   | [ULN2803A](https://cdn-shop.adafruit.com/datasheets/ULN2803A.pdf)               | [search](https://octopart.com/search?q=ULN2803APG) | manual |                                                 |
| [XR2206CP](parts/xr2206cp.md) | 1   | Monolithic function generator IC            | [XR2206](https://cdn.sparkfun.com/assets/8/a/b/3/9/XR2206.pdf)                  | [search](https://octopart.com/search?q=XR2206CP)   | manual |                                                 |

## Transistors (DDR / USSR vintage set)

Single set of labelled vintage Cyrillic-prefix transistors (К → K transliteration: KU = high-power, KT = small/medium-signal, KF = high-voltage). Qty 1 of each unless noted. The *Equivalent / marking* column carries either the Western cross-reference or the physical dot-marking from the chip body.

| Part   | Type | Equivalent / marking     | Package | Umax  | Imax   | Qty | Source |
| ------ | ---- | ------------------------ | ------- | ----- | ------ | --- | ------ |
| KF 470 | PNP  |                          | TO-126  | 250 V | 30 mA  | 1   | manual |
| KT 209 | PNP  | X.1                      | TO-92   | 60 V  | 300 mA | 1   | manual |
| KT 326 | PNP  | A 3                      | TO-92   | 15 V  | 50 mA  | 1   | manual |
| KT 345 | PNP  | 2× weiß, 1× rot, 1× blau | TO-92   | 12 V  | 300 mA | 1   | manual |
| KT 368 | NPN  | 1 weißer Punkt           | TO-92   | 15 V  | 30 mA  | 1   | manual |
| KT 382 | NPN  |                          | Bild 1  | 150 V | 20 mA  | 1   | manual |
| KT 502 | PNP  | weißer + gelber Punkt    | TO-92   | 25 V  | 300 mA | 1   | manual |
| KT 503 | NPN  | 2 weiße Punkte           | TO-92   | 40 V  | 200 mA | 1   | manual |
| KT 801 | NPN  | BC 141                   | Bild 2  | 60 V  | 2 A    | 1   | manual |
| KT 805 | NPN  | BD 243                   | TO-220  | 160 V | 5 A    | 1   | manual |
| KU 601 | NPN  | BDY 10                   | TO-3    | 60 V  | 2 A    | 1   | manual |

## Sensors

| Part | Qty | Description | Datasheet | Octopart | Source | Notes |
| ---- | --- | ----------- | --------- | -------- | ------ | ----- |
|      |     |             |           |          | manual |       |

## Modules / breakouts

| Part | Qty | Description | Datasheet | Octopart | Source | Notes |
| ---- | --- | ----------- | --------- | -------- | ------ | ----- |
|      |     |             |           |          | manual |       |

## Bulk / kits

Loose-grained — we record that we have these on hand without tracking exact counts. For the two named assortments below, contents are typical-Conrad-kit values; adjust if a specific value's pieces differ.

### 1/8 W carbon-film resistor set — E12, 10 Ω – 1 MΩ, ~10 pcs / value (~610 total)

| Decade range | E12 values                                                       |
| ------------ | ---------------------------------------------------------------- |
| Ω            | 10, 12, 15, 18, 22, 27, 33, 39, 47, 56, 68, 82                   |
| ×10 Ω        | 100, 120, 150, 180, 220, 270, 330, 390, 470, 560, 680, 820       |
| kΩ           | 1.0, 1.2, 1.5, 1.8, 2.2, 2.7, 3.3, 3.9, 4.7, 5.6, 6.8, 8.2       |
| ×10 kΩ       | 10, 12, 15, 18, 22, 27, 33, 39, 47, 56, 68, 82                   |
| ×100 kΩ      | 100, 120, 150, 180, 220, 270, 330, 390, 470, 560, 680, 820       |
| MΩ           | 1.0                                                              |

### 50-piece electrolytic capacitor assortment — ~5 pcs / value, 10 values

| Value    | Voltage (typ.) | Pieces |
| -------- | -------------- | ------ |
| 1 µF     | 50 V           | 5      |
| 2.2 µF   | 50 V           | 5      |
| 4.7 µF   | 50 V           | 5      |
| 10 µF    | 50 V           | 5      |
| 22 µF    | 50 V           | 5      |
| 47 µF    | 25 V           | 5      |
| 100 µF   | 25 V           | 5      |
| 220 µF   | 25 V           | 5      |
| 470 µF   | 16 V           | 5      |
| 1000 µF  | 16 V           | 5      |

### Loose / discrete on hand

Items bought as specific bags or strips, separate from the named assortment kits above.

| Part               | Description                                 | Qty | Source |
| ------------------ | ------------------------------------------- | --- | ------ |
| 1N4148             | Signal diode (Si, 100 V, 200 mA)            | 1   | manual |
| 1N5404             | General-purpose rectifier (3 A, 400 V)      | 1   | manual |
| Elko 0.1 µF / 50 V | Radial electrolytic, 105 °C, 4×5 mm, RM 1.5 | 10  | manual |
| P600B              | General-purpose rectifier (6 A, 100 V)      | 1   | manual |
| UF4007             | Ultra-fast recovery rectifier (1 A, 1000 V) | 1   | manual |
