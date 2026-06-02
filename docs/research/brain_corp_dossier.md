# Brain Corp Dossier

This is primarily external research. When CORE status is mentioned for
conversation framing, it is reconciled to `docs/claims_ledger.md` on main.

## Snapshot

Brain Corp presents BrainOS as a deployed autonomy platform for commercial
robots, with applications across cleaning, inventory, remote site management,
and newer physical-AI directions. Public materials position BrainOS as a
platform combining robotic autonomy, analytics/operations management, and
autonomy services. The BrainOS page states that the platform integrates a
sensor kit, UL-certified controller, and autonomy software for perception,
motion planning, localization, and navigation. [BrainOS platform](https://www.braincorp.com/brainos)

Brain Corp's safety page emphasizes computer vision, 3D LiDAR, real-time path
adjustment, global replanning, path optimization, redundant safety systems, and
real-time obstacle detection. It also states the controller has independent UL
60730-1 and SIL2 verification and gives public fleet scale/reliability claims.
[Brain Corp safety](https://www.braincorp.com/safety)

## Public Architecture Reading

The public architecture is a deployed robotics autonomy stack:

- Sensors and perception: computer vision and 3D LiDAR are explicitly named in
  safety materials.
- Localization/navigation/planning: BrainOS describes perception, precise motion
  planning, localization, and advanced navigation.
- Runtime safety: the safety page describes layered and redundant safety, plus
  obstacle detection in dynamic environments.
- Fleet/ops layer: BrainOS includes BrainOS Mobile, Fleet Ops Portal, weekly
  summaries, remote monitoring/diagnostics, and remote route optimization.
- Data flywheel: BrainOS describes "crowdsource learning," where field robot
  experience is applied across the fleet.

The important CTO inference: Brain Corp does not need a generic "robot brain."
They already operate a vertically integrated autonomy-plus-operations platform.
Any CORE conversation must be about a narrow substrate underneath or adjacent to
decision accountability, not replacing their stack.

## Safety and Determinism Positioning

Brain Corp's public "deterministic safety" equivalent sits in conventional
robotics safety architecture: sensors, obstacle detection, real-time replanning,
multi-layer redundancy, controller certification, and fleet operational support.
Public materials do not describe an inspectable cognitive trace substrate that
turns an abstract decision into a replayable refusal/proceed/stop proof. That is
the possible opening for CORE, but it should be framed as a gap hypothesis, not
as a proven product-market fit.

## Partnerships and Commercial Signals

Tennant is the clearest floor-care partner signal. Tennant and Brain Corp
announced an exclusive technology agreement in February 2024 to accelerate
robotic floor-cleaning innovation. Tennant said Brain Corp technology powered
more than 6,500 Tennant cleaning robots in the field and described the X4 ROVR
as the first of planned future AMR cleaning products powered by Brain Corp's
next-generation technology for Tennant equipment. [Tennant/Brain Corp agreement](https://investors.tennantco.com/news/news-details/2024/Tennant-Company-and-Brain-Corp-Sign-Exclusive-Technology-Agreement-To-Accelerate-Robotic-Floor-Cleaning-Innovation-and-Adoption/default.aspx)

Tennant's X4 ROVR release says the machine is powered by the next-generation
BrainOS Robotics Platform and emphasizes computer vision, compact dimensions,
and operation in narrow/congested spaces. [X4 ROVR release](https://investors.tennantco.com/news/news-details/2024/Tennant-Announces-Full-Specification--Capabilities-of-X4-ROVR-Autonomous-Floor-Cleaning-Machine-its-First-Purpose-Built-Robotic-Scrubber-/default.aspx)

SoftBank Robotics' Whiz materials also name BrainOS. SoftBank Robotics America
describes Whiz as powered by BrainOS, and SoftBank Robotics Group describes
Whiz/Whiz i as co-developed with Brain Corp in 2017. [SoftBank Robotics Whiz](https://us.softbankrobotics.com/whiz), [SoftBank Robotics solution page](https://www.softbankrobotics.com/solution/)

Brain Corp also announced a May 20, 2026 UC San Diego collaboration focused on
semantic mapping and contextual grounding for physical AI. That announcement is
especially relevant because it names the same adjacent problem space where CORE
should avoid overclaiming: contextual understanding, grounding, and reliability
in complex physical environments. [Brain Corp/UC San Diego](https://www.braincorp.com/resources/brain-corp-and-uc-san-diego-partner-to-advance-the-foundational-intelligence-layer-for-physical-ai)

## Eugene Izhikevich Lineage

Brain Corp's own about page identifies Dr. Eugene Izhikevich as co-founder and
chairman. It says the company began in 2009 with computational neuroscientists
providing research services, guided by Izhikevich, and later launched BrainOS in
2014. The same page ties Izhikevich to spiking-network theory, a large
thalamo-cortical model, the Neurosciences Institute, and Scholarpedia.
[Brain Corp about](https://www.braincorp.com/about)

Takeaway for the CTO conversation: do not present CORE's geometric/cognitive
language as exotic relative to Brain Corp. Their origin story already includes
computational neuroscience and brain-inspired robotics. The differentiator must
be a concrete accountable substrate, not philosophical novelty.

## Patent Signals

US11467602B2, assigned to Brain Corp, is titled "Systems and methods for
training a robot to autonomously travel a route." The patent page names route,
map, robot, and user as key terms and describes learning a route by
demonstration, mapping/localization, autonomous navigation, sensor data,
actuator association, map evaluation/correction, and cases where the robot
determines not to autonomously navigate a portion of a route. [US11467602B2](https://patents.google.com/patent/US11467602B2/en)

This patent signal reinforces that Brain Corp's core lane is teach/repeat,
mapping, localization, navigation, route quality, and commercial cleaning
robotics. CORE should not enter the conversation as a competing route-learning
or navigation system.

## Adjacent Players

- Avidbots: autonomous floor-care competitor. Avidbots public autonomy material
  says its proprietary AI software powers Neo for autonomous floor scrubbing.
  [Avidbots autonomy PDF](https://avidbots.com/assets/Knowledge/Avidbots_Autonomy.pdf)
- SoftBank Robotics: Whiz is a commercial cleaning robot line, with official
  pages naming BrainOS and Brain Corp involvement. [Whiz](https://us.softbankrobotics.com/whiz)
- Locus Robotics: warehouse AMR/orchestration competitor in a different
  vertical. Locus publicly describes AMRs, LocusONE orchestration, Locus Origin,
  Locus Vector, and newer Locus Array for more autonomous fulfillment.
  [Locus Robotics](https://www.locusrobotics.com/)

## Gap CORE Can Honestly Target

The precise gap is not perception, not navigation, not motion planning, and not
fleet operations. Brain Corp already owns those deployed surfaces.

The possible gap is a substrate-level accountability layer for bounded decisions:

- preserve an abstract decision record as a deterministic trace;
- distinguish proceed, stop, and refusal;
- refuse under-determined input rather than forcing a fluent answer;
- make replay equality a first-class artifact;
- expose invariant checks and refusal reason in a canonical protocol.

The current AMR demo should be described only as a preparation artifact that
shows this shape over simulated records. It does not prove deployment readiness.
Ledger framing keeps that boundary sharp: no CORE domain is at `expert`;
`audit-passed` means claim-shape compliance, not raw capability; text is an
active modality, audio is substrate with its gate CLOSED, and vision/motor are
proposed only. Determinism should be framed as byte-stable trace/digest evidence
and fail-closed drift detection, not robotics-grade control.

## Conversation Posture

Strong opening:

"BrainOS is the robotics stack. We are not here to claim perception, planning,
or motor control. We prepared a tiny simulated AMR-adjacent accountability demo
to discuss whether a deterministic refusal/replay substrate could be useful
beneath bounded decisions in a system like yours. The demo is a preparation
artifact over simulated records, not deployment readiness."

Weak opening:

"CORE is a new kind of robot intelligence that could sit under BrainOS."

## Source List

- [BrainOS platform](https://www.braincorp.com/brainos)
- [Brain Corp safety](https://www.braincorp.com/safety)
- [Brain Corp about](https://www.braincorp.com/about)
- [Brain Corp / UC San Diego physical AI collaboration](https://www.braincorp.com/resources/brain-corp-and-uc-san-diego-partner-to-advance-the-foundational-intelligence-layer-for-physical-ai)
- [Tennant / Brain Corp exclusive technology agreement](https://investors.tennantco.com/news/news-details/2024/Tennant-Company-and-Brain-Corp-Sign-Exclusive-Technology-Agreement-To-Accelerate-Robotic-Floor-Cleaning-Innovation-and-Adoption/default.aspx)
- [Tennant X4 ROVR release](https://investors.tennantco.com/news/news-details/2024/Tennant-Announces-Full-Specification--Capabilities-of-X4-ROVR-Autonomous-Floor-Cleaning-Machine-its-First-Purpose-Built-Robotic-Scrubber-/default.aspx)
- [Tennant T380AMR product page](https://www.tennantco.com/en_us/1/machines/scrubbers/product.t380amr.robotic-floor-scrubber.M-T380AMR.html)
- [SoftBank Robotics Whiz](https://us.softbankrobotics.com/whiz)
- [SoftBank Robotics solution page](https://www.softbankrobotics.com/solution/)
- [US11467602B2 patent](https://patents.google.com/patent/US11467602B2/en)
- [Avidbots autonomy PDF](https://avidbots.com/assets/Knowledge/Avidbots_Autonomy.pdf)
- [Locus Robotics](https://www.locusrobotics.com/)
