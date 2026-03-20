import { handleApiError } from "@acc/api/base";
import { getStats } from "@acc/api/calculations/calculations";
import { MoleculeSetStats } from "@acc/api/calculations/types";
import { UploadResponse } from "@acc/api/files/types";
import { AdvancedSettings } from "@acc/components/home/advanced-settings";
import { MissingHydrogensWarning } from "@acc/components/shared/alerts/missing-hydrogen-warning";
import { Busy } from "@acc/components/shared/busy";
import { ErrorAlert } from "@acc/components/shared/error-alert";
import { Button } from "@acc/components/ui/button";
import { Card } from "@acc/components/ui/card";
import { Form } from "@acc/components/ui/form";
import { Input } from "@acc/components/ui/input";
import { Label } from "@acc/components/ui/label";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@acc/components/ui/popover";
import { useFileStatsContext } from "@acc/lib/hooks/contexts/use-file-stats-context";
import { useComputationMutations } from "@acc/lib/hooks/mutations/use-calculations";
import { useFileMutations } from "@acc/lib/hooks/mutations/use-files";
import { zodResolver } from "@hookform/resolvers/zod";
import { ChevronsUpDown } from "lucide-react";
import { useState } from "react";
import { Controller, useForm } from "react-hook-form";
import { createSearchParams, useNavigate } from "react-router";
import { toast } from "sonner";
import z from "zod";

const computeSchema = z.object({
  files: z
    .instanceof(FileList, { message: "Files are required." })
    .refine((files) => files.length > 0),
  settings: z.object({
    readHetatm: z.boolean(),
    ignoreWater: z.boolean(),
    permissiveTypes: z.boolean(),
  }),
});

type ComputeType = z.infer<typeof computeSchema>;

export const Compute = () => {
  const navigate = useNavigate();
  const { fileUploadMutation } = useFileMutations();
  const { computeMutation, setupMutation } = useComputationMutations();
  const fileStatsContext = useFileStatsContext();

  const [missingHydrogens, setMissingHydrogens] = useState<boolean>(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadResponse, setUploadResponse] = useState<UploadResponse | null>(
    null
  );
  const [statsMap, setStatsMap] = useState<Record<string, MoleculeSetStats>>(
    {}
  );

  const form = useForm<ComputeType>({
    resolver: zodResolver(computeSchema),
    defaultValues: {
      files: undefined,
      settings: {
        readHetatm: true,
        ignoreWater: false,
        permissiveTypes: true,
      },
    },
  });

  const onSubmit = async (data: ComputeType) => {
    if (uploadResponse === null) {
      return;
    }

    const compId = crypto.randomUUID();

    fileStatsContext.set(
      compId,
      Object.fromEntries(
        uploadResponse.map((f) => [f.fileHash, statsMap[f.fileHash]])
      )
    );

    await computeMutation.mutateAsync(
      {
        fileHashes: uploadResponse.map((file) => file.fileHash),
        configs: [],
        settings: data.settings,
        computationId: compId,
      },
      {
        onError: (error) => toast.error(handleApiError(error)),
        onSuccess: (compId) => {
          void navigate({
            pathname: "results",
            search: createSearchParams({
              comp_id: compId,
            }).toString(),
          });
        },
      }
    );
  };

  const onFileChange = async (data: FileList | null) => {
    setMissingHydrogens(false);
    setUploadError(null);

    if (!data) {
      return;
    }

    await fileUploadMutation.mutateAsync(data, {
      onError: (error) => {
        setUploadError(handleApiError(error));
        form.resetField("files");
      },
      onSuccess: async (uploadResponse) => {
        setUploadResponse(uploadResponse);

        const promises = uploadResponse.map(({ fileHash }) =>
          getStats(fileHash)
            .then((stat) => ({ fileHash, stat, error: null }))
            .catch(() => null)
        );
        const stats = (await Promise.all(promises)).filter(
          (item) => item !== null && item.stat !== null
        ) as { fileHash: string; stat: MoleculeSetStats }[];

        setStatsMap(
          stats.reduce(
            (prev, curr) => {
              prev[curr.fileHash] = curr.stat;
              return prev;
            },
            {} as Record<string, MoleculeSetStats>
          )
        );

        const isMissingHydrogen = stats.some(
          (stat) =>
            (stat.stat.atomTypeCounts.find(({ symbol }) => symbol === "H")
              ?.count ?? 0) === 0
        );
        setMissingHydrogens(isMissingHydrogen);
      },
    });
  };

  const onSetup = async (data: ComputeType) => {
    if (uploadResponse === null) {
      return;
    }

    await setupMutation.mutateAsync(
      {
        fileHashes: uploadResponse.map((file) => file.fileHash),
        settings: data.settings,
      },
      {
        onError: () =>
          toast.error("Unable to setup computation. Try again later."),
        onSuccess: (compId) => {
          fileStatsContext.set(
            compId,
            Object.fromEntries(
              uploadResponse.map((f) => [f.fileHash, statsMap[f.fileHash]])
            )
          );
          void navigate({
            pathname: "setup",
            search: createSearchParams({
              comp_id: compId,
            }).toString(),
          });
        },
      }
    );
  };

  return (
    <Card className="w-11/12 md:w-4/5 rounded-none shadow-xl mx-auto p-4 max-w-content mb-12 mt-0 xs:mt-8 md:mt-0 relative">
      <Busy isBusy={computeMutation.isPending || fileUploadMutation.isPending}>
        {fileUploadMutation.isPending && "Uploading files..."}
        {computeMutation.isPending && "Computing charges..."}
      </Busy>
      <h2 className="text-5xl text-primary font-bold">Compute</h2>
      <Form {...form}>
        <form onSubmit={form.handleSubmit(onSubmit)}>
          <div className="my-4 flex flex-col gap-2">
            <Label className="font-bold text-lg">Upload structures</Label>
            <Controller
              name="files"
              control={form.control}
              render={({ field }) => (
                <Input
                  id="files"
                  type="file"
                  accept=".sdf,.mol2,.pdb,.mmcif,.cif"
                  className="border-2 border-primary cursor-pointer xs:w-fit max-w-full"
                  onChange={(e) => {
                    field.onChange(e.target.files);
                    void onFileChange(e.target.files);
                  }}
                  onBlur={field.onBlur}
                  ref={field.ref}
                  multiple
                />
              )}
            />
            <p className="text-sm text-black text-opacity-40">
              Supported filetypes are <span className="font-bold">sdf</span>,
              <span className="font-bold"> mol2</span>,
              <span className="font-bold"> pdb</span>,
              <span className="font-bold"> mmcif</span>. You can upload one or
              multiple files at the same time. Maximum allowed upload size is
              <span className="font-bold"> 50 MB</span>.
            </p>
          </div>

          {missingHydrogens && <MissingHydrogensWarning />}
          {uploadError !== null && (
            <ErrorAlert title="Upload error" description={uploadError} />
          )}

          <div className="flex gap-4 flex-col sm:flex-row">
            <Button
              type="submit"
              title="Direct computation of charges using automatically selected empirical charge calculation method."
              disabled={!form.formState.isValid}
            >
              Compute
            </Button>
            <Button
              type="button"
              title="Selection of empirical charge calculation method and its parameters."
              variant={"secondary"}
              disabled={!form.formState.isValid}
              onClick={() => onSetup(form.getValues())}
            >
              Setup Computation
            </Button>
            <Popover>
              <PopoverTrigger asChild>
                <Button variant={"ghost"} disabled={!form.formState.isValid}>
                  Advanced <ChevronsUpDown size={15} />
                </Button>
              </PopoverTrigger>
              <PopoverContent>
                <AdvancedSettings />
              </PopoverContent>
            </Popover>
          </div>
        </form>
      </Form>
    </Card>
  );
};
