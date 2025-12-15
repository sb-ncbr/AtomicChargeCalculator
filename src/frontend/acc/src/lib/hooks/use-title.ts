import { useEffect } from "react";

export const useTitle = (title: string) => {
  const prefix = "Atomic Charge Calculator III | ";

  useEffect(() => {
    const prevTitle = document.title;
    document.title = prefix + title;
    return () => {
      document.title = prevTitle;
    };
  });
};
