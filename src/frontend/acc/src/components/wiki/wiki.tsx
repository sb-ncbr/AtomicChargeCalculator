import WikiMd from "@acc/assets/wiki.md";
import { ScrollArea } from "@acc/components/ui/scroll-area";
import { cn } from "@acc/lib/utils";
import { HTMLAttributes } from "react";

export const Wiki = () => {
  return (
    <main className="mx-auto w-full selection:text-white selection:bg-primary">
      <ScrollArea type="auto">
        <article className="max-w-min mx-auto pb-8">
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
                  <h2
                    className="text-5xl text-primary font-bold pt-8 pb-4"
                    {...props}
                  />
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
                    <img className="m-4 py-4 w-[28%] inline-block" {...props} />
                  );
                }
                return (
                  <img
                    className="border-solid border-primary border-[1px] shadow-lg my-4 p-4"
                    {...props}
                  />
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
                        "border-solid border-[1px] border-primary my-2",
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
      </ScrollArea>
    </main>
  );
};
