import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FormEvent, useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api } from "../api/client";
import { StatusIndicator } from "../components/common/StatusIndicator";
import { useUiStore } from "../store/useUiStore";

export function VacancyDetailPage(): JSX.Element {
  const { vacancyId = "" } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const setSelectedVacancyId = useUiStore((state) => state.setSelectedVacancyId);
  const setActiveProcessingJobId = useUiStore((state) => state.setActiveProcessingJobId);

  const query = useQuery({
    queryKey: ["vacancy", vacancyId],
    queryFn: () => api.vacancies.get(vacancyId),
    enabled: Boolean(vacancyId),
    refetchInterval: 2200
  });

  const [skills, setSkills] = useState<string[]>([]);
  const [newSkill, setNewSkill] = useState("");
  const [skillsWeight, setSkillsWeight] = useState(65);
  const [experienceWeight, setExperienceWeight] = useState(35);

  useEffect(() => {
    if (!query.data) {
      return;
    }
    setSkills(query.data.extractedSkills);
    setSkillsWeight(Math.round(query.data.weights.skills * 100));
    setExperienceWeight(Math.round(query.data.weights.experience * 100));
    setSelectedVacancyId(query.data.id);
  }, [query.data, setSelectedVacancyId]);

  const updateMutation = useMutation({
    mutationFn: () =>
      api.vacancies.update(vacancyId, {
        extractedSkills: skills,
        weights: {
          skills: skillsWeight / 100,
          experience: experienceWeight / 100
        }
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["vacancy", vacancyId] });
      queryClient.invalidateQueries({ queryKey: ["vacancies"] });
      queryClient.invalidateQueries({ queryKey: ["shortlists"] });
    }
  });

  const generateMutation = useMutation({
    mutationFn: () => api.vacancies.generateShortlist(vacancyId),
    onSuccess: (payload) => {
      queryClient.invalidateQueries({ queryKey: ["vacancies"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      if (payload.ready) {
        navigate(`/shortlists?vacancy=${vacancyId}`);
        return;
      }
      if (payload.processingJobId) {
        setActiveProcessingJobId(payload.processingJobId);
        navigate(`/processing/${payload.processingJobId}`);
      }
    }
  });

  if (!query.data) {
    return <section className="screen is-active"><p className="mono-mute">Vacancy not found.</p></section>;
  }

  function addSkill(event: FormEvent<HTMLFormElement>): void {
    event.preventDefault();
    const value = newSkill.trim().toLowerCase();
    if (!value || skills.includes(value)) {
      return;
    }
    setSkills((prev) => [...prev, value]);
    setNewSkill("");
  }

  return (
    <section className="screen is-active">
      <header className="screen-header">
        <div>
          <h1 className="screen-title">{query.data.title}</h1>
          <p className="screen-sub">vacancy configuration · weights &amp; skills</p>
        </div>
        <StatusIndicator status={query.data.status} />
      </header>
      <hr className="screen-divider" />

      <div className="two-col">
        <div className="panel">
          <div className="panel-header">
            <h2 className="panel-title">job description</h2>
          </div>
          <div className="panel-body stack-16">
            <p className="muted">{query.data.description}</p>
            <div>
              <span className="mono-mute">extracted skills</span>
              <div style={{ marginTop: 8, display: "flex", flexWrap: "wrap", gap: 6 }}>
                {skills.map((skill) => (
                  <button
                    type="button"
                    key={skill}
                    className="badge"
                    style={{ cursor: "pointer", background: "none", border: "1px solid var(--hairline)" }}
                    onClick={() => setSkills((prev) => prev.filter((item) => item !== skill))}
                  >
                    {skill} ×
                  </button>
                ))}
              </div>
            </div>
            <form style={{ display: "flex", gap: 8 }} onSubmit={addSkill}>
              <input
                className="field"
                type="text"
                value={newSkill}
                onChange={(event) => setNewSkill(event.target.value)}
                placeholder="add skill"
              />
              <button type="submit" className="btn btn-ghost btn-sm">+ add</button>
            </form>
          </div>
        </div>

        <div className="panel">
          <div className="panel-header">
            <h2 className="panel-title">ranking weights</h2>
          </div>
          <div className="panel-body stack-16">
            <div>
              <div className="row-between" style={{ marginBottom: 8 }}>
                <span className="mono-mute">skills weight</span>
                <span className="num" style={{ fontWeight: 500 }}>{skillsWeight}%</span>
              </div>
              <input
                type="range"
                className="slider"
                min={20}
                max={80}
                value={skillsWeight}
                style={{ width: "100%" }}
                onChange={(event) => setSkillsWeight(Number(event.target.value))}
              />
            </div>
            <div>
              <div className="row-between" style={{ marginBottom: 8 }}>
                <span className="mono-mute">experience weight</span>
                <span className="num" style={{ fontWeight: 500 }}>{experienceWeight}%</span>
              </div>
              <input
                type="range"
                className="slider"
                min={20}
                max={80}
                value={experienceWeight}
                style={{ width: "100%" }}
                onChange={(event) => setExperienceWeight(Number(event.target.value))}
              />
            </div>
            <button type="button" className="btn btn-ghost btn-sm" onClick={() => updateMutation.mutate()}>
              {updateMutation.isPending ? "saving..." : "save configuration"}
            </button>
          </div>
        </div>
      </div>

      <div style={{ height: 24 }} />

      <div className="panel">
        <div className="panel-body">
          <button type="button" className="btn btn-primary" onClick={() => generateMutation.mutate()}>
            {generateMutation.isPending ? "running..." : "→ generate shortlist"}
          </button>
        </div>
      </div>
    </section>
  );
}

