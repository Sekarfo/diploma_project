import { useMutation, useQueryClient } from "@tanstack/react-query";
import { FormEvent, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";
import { useUiStore } from "../store/useUiStore";

const skillHints = ["python", "sql", "fastapi", "xgboost", "react", "typescript", "docker", "machine learning"];

function inferSkills(input: string): string[] {
  const lower = input.toLowerCase();
  return skillHints.filter((skill) => lower.includes(skill));
}

export function VacancyCreatePage(): JSX.Element {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const setSelectedVacancyId = useUiStore((state) => state.setSelectedVacancyId);
  const setActiveProcessingJobId = useUiStore((state) => state.setActiveProcessingJobId);

  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");

  const extractedPreview = useMemo(() => inferSkills(`${title} ${description}`), [title, description]);

  const mutation = useMutation({
    mutationFn: api.vacancies.create,
    onSuccess: (response) => {
      setSelectedVacancyId(response.vacancy.id);
      queryClient.invalidateQueries({ queryKey: ["vacancies"] });
      setActiveProcessingJobId(response.processingJob.id);
      queryClient.invalidateQueries({ queryKey: ["vacancies"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      navigate(`/processing/${response.processingJob.id}`);
    }
  });

  function onSubmit(event: FormEvent<HTMLFormElement>): void {
    event.preventDefault();
    if (!title.trim() || !description.trim()) return;
    mutation.mutate({ title, description });
  }

  return (
    <section className="screen is-active">
      <header className="screen-header">
        <div>
          <h1 className="screen-title">create vacancy</h1>
          <p className="screen-sub">define the role spec the ranker will score candidates against</p>
        </div>
      </header>
      <hr className="screen-divider" />

      <form onSubmit={onSubmit}>
        <div className="panel">
          <div className="panel-header">
            <h2 className="panel-title">vacancy spec</h2>
          </div>
          <div className="panel-body stack-16">
            <label style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              <span className="mono-mute">job title</span>
              <input
                className="field"
                type="text"
                placeholder="Senior ML Engineer"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
              />
            </label>
            <label style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              <span className="mono-mute">job description</span>
              <textarea
                className="field"
                style={{ height: "auto", minHeight: 140 }}
                rows={8}
                placeholder="Describe role, required skills, and expected experience."
                value={description}
                onChange={(e) => setDescription(e.target.value)}
              />
            </label>
            <div>
              <span className="mono-mute">extracted skills preview: </span>
              {extractedPreview.length > 0 ? (
                extractedPreview.map((skill) => (
                  <span key={skill} className="badge" style={{ marginRight: 6 }}>{skill}</span>
                ))
              ) : (
                <span className="mono-mute">no explicit skills detected yet.</span>
              )}
            </div>
            <button type="submit" className="btn btn-primary" disabled={mutation.isPending}>
              {mutation.isPending ? "submitting..." : "+ submit vacancy"}
            </button>
          </div>
        </div>
      </form>
    </section>
  );
}
