import { useRef } from "react";

import { createConversation } from "../api/conversations.js";
import { getArticle } from "../api/articles.js";
import { getAuthSessionVersion } from "../utils/tokenStorage.js";
import { toArticleView, toConversationView } from "../utils/historyDataAdapters.js";

export default function useConversationWithFile() {
  const pendingUploads = useRef(new WeakMap()); // 같은 파일로 요청이 중복 실행되는 것을 방지하는 값

  async function createConversationWithFile({ file, visibility }) {
    const requestSessionVersion = getAuthSessionVersion();
    let result = pendingUploads.current.get(file); // 기사 조회만 실패했다면 이미 생성한 대화를 다시 사용합니다.

    if (!result) {
      result = await createConversation({
        file,
        title: file.name.trim().slice(0, 255),
        visibility,
      });
      pendingUploads.current.set(file, result);
    }

    const articleData = await getArticle({ articleId: result.article_id });

    if (getAuthSessionVersion() !== requestSessionVersion) return;
    pendingUploads.current.delete(file);

    return {
      article: toArticleView(articleData, file),
      conversation: toConversationView(result),
    };
  }

  return createConversationWithFile;
}
