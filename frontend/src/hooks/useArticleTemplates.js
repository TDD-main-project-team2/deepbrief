import { useEffect, useState } from "react";

import { getTemplateList } from "../api/features";

export default function useArticleTemplates() {
  const [templates, setTemplates] = useState([]);
  const [loadingTemplates, setLoadingTemplates] = useState(true);
  const [templateError, setTemplateError] = useState("");
  const [templateReload, setTemplateReload] = useState(0);

  useEffect(() => {
    let cancelled = false;

    async function loadTemplates() {
      try {
        const result = await getTemplateList();
        if (!cancelled) setTemplates(result);
      } catch {
        if (!cancelled) setTemplateError("템플릿을 불러오지 못했습니다.");
      } finally {
        if (!cancelled) setLoadingTemplates(false);
      }
    }

    loadTemplates();

    return () => {
      cancelled = true;
    };
  }, [templateReload]);

  function retryTemplates() {
    setTemplateError("");
    setLoadingTemplates(true);
    setTemplateReload((value) => value + 1);
  }

  return { templates, loadingTemplates, templateError, retryTemplates };
}
