import WikiMd from "@acc/assets/wiki.md";
import { cn } from "@acc/lib/utils";
import { Separator } from "@radix-ui/react-dropdown-menu";
import { HTMLAttributes } from "react";

export type DocumentatinComponentsProps = {
  getSectionId: (content: string) => string;
};

export const DocumentationComponents = ({
  getSectionId,
}: DocumentatinComponentsProps) => {
  return (
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
            <ul className="ml-4 list-disc marker:text-primary" {...props} />
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
  );
};
