export type DocumentationNavigationProps = {
  contents: string[];
  getSectionId: (content: string) => string;
};

export const DocumentationNavigation = ({
  contents,
  getSectionId,
}: DocumentationNavigationProps) => {
  return (
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
  );
};
