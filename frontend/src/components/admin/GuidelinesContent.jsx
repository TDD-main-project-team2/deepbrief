import { createOrgGuideline, updateOrgGuideline, deleteOrgGuideline } from "../../api/admin.js";
import TemplateGuidelineContent from "./TemplateGuidelineContent.jsx";

export default function GuidelinesContent(props) {
  return (
    <TemplateGuidelineContent
      {...props}
      onCreate={createOrgGuideline}
      onEdit={updateOrgGuideline}
      onDelete={deleteOrgGuideline}
      type="guidelines"
      title="작성 지침 관리"
      description="기사 검토와 평가에 적용할 조직의 작성 기준을 관리합니다."
    />
  );
}
