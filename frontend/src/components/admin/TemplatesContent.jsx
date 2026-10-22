import { createOrgTemplate, updateOrgTemplate, deleteOrgTemplate } from "../../api/admin.js";
import TemplateGuidelineContent from "./TemplateGuidelineContent.jsx";

export default function TemplatesContent(props) {
  return (
    <TemplateGuidelineContent
      {...props}
      type="templates"
      title="템플릿 관리"
      caption="TEMPLATE MANAGEMENT"
      description="기사 작성 시 활용할 조직 공통 템플릿을 관리합니다."
      onCreate={createOrgTemplate}
      onEdit={updateOrgTemplate}
      onDelete={deleteOrgTemplate}
    />
  );
}
