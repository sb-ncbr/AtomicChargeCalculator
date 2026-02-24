import { useMolstarContext } from "@acc/lib/hooks/contexts/use-molstar-context";
import { useBehavior } from "@acc/lib/hooks/use-behavior";
import { cn } from "@acc/lib/utils";
import { PluginUIContext } from "molstar/lib/commonjs/mol-plugin-ui/context";
import { LeftPanelControls } from "molstar/lib/commonjs/mol-plugin-ui/left-panel";
import {
  ControlsWrapper,
  DefaultViewport,
  PluginContextContainer,
} from "molstar/lib/commonjs/mol-plugin-ui/plugin";
import { SequenceView } from "molstar/lib/commonjs/mol-plugin-ui/sequence";
import { HTMLAttributes, useEffect, useState } from "react";
import { combineLatest } from "rxjs";

import { Busy, BusySize } from "../shared/busy";
import { Card } from "../ui/card";
import { MolstarColorScale } from "./controls/color-scale";

export type MolstarViewerProps = {
  plugin: PluginUIContext;
  maxCharge?: number;
} & HTMLAttributes<HTMLElement>;

export const MolstarViewer = ({
  plugin,
  maxCharge,
  className,
  ...props
}: MolstarViewerProps) => {
  const [isLoading, setIsLoading] = useState(true);
  const molstarContext = useMolstarContext();
  const showControls = useBehavior(molstarContext.layout.showControls);
  const isExpanded = useBehavior(molstarContext.layout.isExpanded);

  useEffect(() => {
    const subscription = combineLatest([
      plugin.behaviors.state.isUpdating,
      plugin.behaviors.state.isAnimating,
    ]).subscribe((states) => setIsLoading(states.some(Boolean)));

    return () => subscription.unsubscribe();
  }, []);

  return (
    <Card
      {...props}
      className={cn(
        "w-full rounded-none shadow-xl mx-auto p-4 max-w-content mt-4 flex flex-col h-[700px]",
        className
      )}
    >
      <div className="w-full h-full relative">
        <Busy isBusy={isLoading} size={BusySize.Big} delay={100} />
        <div
          className={cn(
            "w-full h-full",
            isExpanded ? "fixed inset-0 z-50" : "relative inset-auto z-auto"
          )}
        >
          <div className="flex flex-row h-full w-full">
            {!isLoading && maxCharge !== undefined && (
              <MolstarColorScale
                maxCharge={maxCharge}
                className={cn(
                  "z-40 w-[120px] h-[40px] absolute",
                  showControls ? "left-[342px] top-[112px]" : "left-3 top-3",
                  isExpanded ? "top-[132px]" : ""
                )}
              />
            )}

            {showControls && (
              <div className="relative max-w-[330px] h-full flex-1">
                <PluginContextContainer plugin={plugin}>
                  <LeftPanelControls />
                </PluginContextContainer>
              </div>
            )}

            <div className="flex flex-1 flex-col h-full w-full">
              {showControls && (
                <div
                  className={cn(
                    "relative",
                    isExpanded ? "h-[120px]" : "h-[100px]"
                  )}
                >
                  <PluginContextContainer plugin={plugin}>
                    <SequenceView />
                  </PluginContextContainer>
                </div>
              )}
              <div className="relative flex-1">
                <PluginContextContainer plugin={plugin}>
                  <DefaultViewport />
                </PluginContextContainer>
              </div>
            </div>
            {showControls && (
              <div className="relative max-w-[300px] h-full flex-1">
                <PluginContextContainer plugin={plugin}>
                  <ControlsWrapper />
                </PluginContextContainer>
              </div>
            )}
          </div>
        </div>
      </div>
    </Card>
  );
};
