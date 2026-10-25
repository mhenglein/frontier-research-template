/-!
# Optional formal lane

This file contains an infrastructure smoke theorem only. It is not a result
about the research problem that a new project will study. Replace it with
small, named claims once their definitions and hypotheses have been reviewed.
-/

namespace FrontierResearch

theorem infrastructure_smoke (p : Prop) : p → p := by
  intro hp
  exact hp

end FrontierResearch
