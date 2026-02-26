import WikiMd from "@acc/assets/wiki.md";
import { ScrollArea } from "@acc/components/ui/scroll-area";
import { cn } from "@acc/lib/utils";
import { HTMLAttributes, useEffect, useRef, useState } from "react";

import { Separator } from "../ui/separator";

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
            <WikiMd
              components={{
                a(props: HTMLAttributes<HTMLAnchorElement>) {
                  return (
                    <a
                      target="_blank"
                      referrerPolicy="no-referrer"
                      className="text-primary hover:underline"
                      rel="noreferrer"
                      {...props}
                    />
                  );
                },
                h1(props: HTMLAttributes<HTMLHeadingElement>) {
                  return (
                    <>
                      <Separator className="first:hidden my-4" />

                      <div className="relative">
                        <div
                          id={getSectionId(`${props?.children ?? ""}`)}
                          className="absolute bottom-40"
                        ></div>
                        <h2
                          className="text-3xl xl:text-5xl text-primary font-bold mb-2"
                          {...props}
                        />
                      </div>
                    </>
                  );
                },
                h2(props: HTMLAttributes<HTMLHeadingElement>) {
                  return (
                    <h3
                      className="capitalize font-bold text-primary text-xl mb-1 mt-2"
                      {...props}
                    />
                  );
                },
                strong(props: HTMLAttributes<HTMLElement>) {
                  return <strong className="font-bold" {...props} />;
                },
                img(props: HTMLAttributes<HTMLImageElement>) {
                  if (["bas", "cartoon", "surface"].includes(props.alt)) {
                    return (
                      <img
                        className="m-4 py-4 w-[25%] max-w-full inline-block box-content"
                        {...props}
                      />
                    );
                  }
                  return (
                    <span className="border-solid border-primary border shadow-lg my-4 p-4 max-w-full box-content inline-block">
                      <img {...props} />
                    </span>
                  );
                },
                li(props: HTMLAttributes<HTMLLIElement>) {
                  return <li {...props} />;
                },
                ul(props: HTMLAttributes<HTMLUListElement>) {
                  return (
                    <ul
                      className="ml-4 list-disc marker:text-primary"
                      {...props}
                    />
                  );
                },
                p(props: HTMLAttributes<HTMLParagraphElement>) {
                  return <p className="text-justify" {...props} />;
                },
                code: ({ ...props }) => {
                  const { className, children, ...rest } = props;
                  if (className?.includes("hljs")) {
                    // highlightjs code block
                    return (
                      <code
                        className={cn(
                          "block overflow-x-auto border-solid border border-primary my-2 box-content",
                          className
                        )}
                        {...rest}
                      >
                        {children}
                      </code>
                    );
                  }
                  return (
                    <code
                      className="bg-muted text-foreground border border-border/50 px-1.5 py-0.5 rounded-md text-sm font-mono whitespace-nowrap"
                      {...rest}
                    >
                      {children}
                    </code>
                  );
                },
              }}
            />
          </article>
          <aside className="hidden min-w-fit lg:block relative ">
            <div className="fixed">
              <h3 className="font-bold">Contents</h3>
              <ul>
                {contents.map((content, index) => {
                  return (
                    <li key={index} className="list-disc text-primary">
                      <a
                        href={`#${getSectionId(content)}`}
                        className="text-primary hover:underline"
                      >
                        {content}
                      </a>
                    </li>
                  );
                })}
              </ul>
            </div>
          </aside>
        </div>
      </ScrollArea>
    </main>
  );
};
