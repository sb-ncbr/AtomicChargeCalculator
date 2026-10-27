import { MolstarContext } from "@acc/lib/contexts/molstar-context";
import { useContext, useEffect, useState } from "react";
import { BehaviorSubject } from "rxjs";

export type MolstarContextHookType = {
  layout: {
    isFullScreen: BehaviorSubject<boolean>;
    isExpanded: BehaviorSubject<boolean>;
    showControls: BehaviorSubject<boolean>;
  };
};

export const useMolstarContext = (): MolstarContextHookType => {
  const context = useContext(MolstarContext);

  if (context === null) {
    throw Error("Molstar context is null.");
  }

  const [fullScreenSubject] = useState(
    () =>
      new BehaviorSubject<boolean>(
        context.plugin?.layout.state.expandToFullscreen ?? false
      )
  );
  const [isExpandedSubject] = useState(
    () =>
      new BehaviorSubject<boolean>(
        context.plugin?.layout.state.isExpanded ?? false
      )
  );
  const [showControlsSubject] = useState(
    () =>
      new BehaviorSubject<boolean>(
        context.plugin?.layout.state.showControls ?? false
      )
  );

  useEffect(() => {
    const subscription = context.plugin?.layout.events.updated.subscribe(() => {
      fullScreenSubject.next(
        context.plugin?.layout.state.expandToFullscreen ?? false
      );
      isExpandedSubject.next(context.plugin?.layout.state.isExpanded ?? false);
      showControlsSubject.next(
        context.plugin?.layout.state.showControls ?? false
      );
    });

    return () => {
      subscription?.unsubscribe();
    };
  }, [context, fullScreenSubject, isExpandedSubject, showControlsSubject]);

  return {
    layout: {
      isFullScreen: fullScreenSubject,
      isExpanded: isExpandedSubject,
      showControls: showControlsSubject,
    },
  };
};
