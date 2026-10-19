import {
  askQuestion,
  formatArticle,
  checkDuplicates,
  evaluateArticle,
  recommendKeywords,
  recommendTitle,
  recommendIdeas,
} from "../api/features.js";

export const chatFeatureConfig = {
  qa: { api: askQuestion, pendingText: "답변을 생성하고 있습니다..." },
  format: { api: formatArticle, pendingText: "기사를 검토하고 있습니다..." },
  duplicate: { api: checkDuplicates, pendingText: "기사를 검토하고 있습니다..." },
  evaluation: { api: evaluateArticle, pendingText: "기사를 검토하고 있습니다..." },
  keywords: { api: recommendKeywords, pendingText: "추천 내용을 생성하고 있습니다..." },
  title: { api: recommendTitle, pendingText: "추천 내용을 생성하고 있습니다..." },
  ideas: { api: recommendIdeas, pendingText: "추천 내용을 생성하고 있습니다..." },
};
