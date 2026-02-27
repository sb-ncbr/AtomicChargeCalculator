import { ScrollArea } from "@acc/components/ui/scroll-area";
import { useEffect, useRef, useState } from "react";

import { DocumentationComponents } from "./documentation-components";
import { DocumentationNavigation } from "./documentation-navigation";

export const Documentation = () => {
  const [contents, setContents] = useState<string[]>([]);
  const articleRef = useRef<HTMLElement>(null);

  const getSectionId = (content: string) =>
    content.toLocaleLowerCase().replaceAll(/\s+/g, "-");

  useEffect(() => {
    if (!articleRef.current) {
      return;
    }

    const headings = Array.from(articleRef.current.querySelectorAll("h2"))
      .map((el) => el.textContent ?? "")
      .filter(Boolean);

    setContents([...new Set(headings)]);
  }, [articleRef]);

  return (
    <main className="mx-auto w-full selection:text-white selection:bg-primary">
      <ScrollArea type="auto">
        <div className="flex flex-col lg:flex-row gap-4 justify-around w-full max-w-[800px] xxl:max-w-[1200px] mx-auto pt-4">
          <article
            ref={articleRef}
            className="pb-8 min-w-0 max-w-[350px] sm:max-w-prose xxl:max-w-[960px] mx-auto flex-shrink"
          >
            <DocumentationComponents getSectionId={getSectionId} />
          </article>
          <DocumentationNavigation
            getSectionId={getSectionId}
            contents={contents}
          />
        </div>
      </ScrollArea>
    </main>
  );
};
