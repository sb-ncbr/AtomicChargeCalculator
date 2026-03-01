import { MolstarContext } from "@acc/lib/contexts/molstar-context";
import { useContext, useEffect, useRef } from "react";
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

  const isFullScreenRef = useRef<BehaviorSubject<boolean>>(
    new BehaviorSubject<boolean>(
      context.plugin?.layout.state.expandToFullscreen ?? false
    )
  );
  const isExpandedRef = useRef<BehaviorSubject<boolean>>(
    new BehaviorSubject<boolean>(
      context.plugin?.layout.state.isExpanded ?? false
    )
  );
  const showControlsRef = useRef<BehaviorSubject<boolean>>(
    new BehaviorSubject<boolean>(
      context.plugin?.layout.state.showControls ?? false
    )
  );

  useEffect(() => {
    const fullScreenSubject = isFullScreenRef.current;
    const isExpandedSubject = isExpandedRef.current;
    const showControlsSubject = showControlsRef.current;

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
  }, [context]);

  return {
    layout: {
      isFullScreen: isFullScreenRef.current,
      isExpanded: isExpandedRef.current,
      showControls: showControlsRef.current,
    },
  };
};
