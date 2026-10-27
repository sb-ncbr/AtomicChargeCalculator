import { handleApiError } from "@acc/api/base";
import { UploadResponse } from "@acc/api/files/types";
import { getSuitableMethodsForFiles } from "@acc/api/methods/methods";
import { MostSuitableMethod } from "@acc/api/methods/types";
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
import { Separator } from "@acc/components/ui/separator";
import { useFileStatsContext } from "@acc/lib/hooks/contexts/use-file-stats-context";
import { useComputationMutations } from "@acc/lib/hooks/mutations/use-calculations";
import { useFileMutations } from "@acc/lib/hooks/mutations/use-files";
import { zodResolver } from "@hookform/resolvers/zod";
import { ChevronsUpDown } from "lucide-react";
import { useEffect, useState } from "react";
import { Controller, useForm, useWatch } from "react-hook-form";
import { createSearchParams, useNavigate } from "react-router";
import { toast } from "sonner";
import z from "zod";

const computeSchema = z.object({
  files: z
    .instanceof(FileList, { error: "Files are required." })
    .refine((files) => files.length > 0),
  settings: z.object({
    readHetatm: z.boolean(),
    ignoreWater: z.boolean(),
    permissiveTypes: z.boolean(),
  }),
});

type ComputeType = z.infer<typeof computeSchema>;

const getMostSuitableMethod = async (
  fileHashes: string[],
  permissiveTypes: boolean
): Promise<MostSuitableMethod> => {
  const suitableMethods = await getSuitableMethodsForFiles(
    fileHashes,
    permissiveTypes
  );
  const method = suitableMethods.methods[0];
  return {
    method,
    parameters: suitableMethods.parameters[method.internalName]?.[0],
  };
};

export const Compute = () => {
  const navigate = useNavigate();
  const { fileUploadMutation } = useFileMutations();
  const { computeMutation, setupMutation } = useComputationMutations();
  const fileStatsContext = useFileStatsContext();

  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadResponse, setUploadResponse] = useState<UploadResponse | null>(
    null
  );
  const [mostSuitableMethod, setMostSuitableMethod] =
    useState<MostSuitableMethod | null>(null);

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
  const watchPermissiveTypes = useWatch({
    control: form.control,
    name: "settings.permissiveTypes",
  });

  // Compute and Setup need the finished upload, which also carries the file stats.
  const isUploaded = form.formState.isValid && uploadResponse !== null;
  const missingHydrogens =
    uploadResponse?.some(
      ({ stats }) =>
        (stats.atomTypeCounts.find(({ symbol }) => symbol === "H")?.count ??
          0) === 0
    ) ?? false;

  const onSubmit = async (data: ComputeType) => {
    if (uploadResponse === null) {
      return;
    }

    const compId = crypto.randomUUID();

    fileStatsContext.set(
      compId,
      Object.fromEntries(uploadResponse.map((f) => [f.fileHash, f.stats]))
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
    setUploadResponse(null);
    setMostSuitableMethod(null);
    setUploadError(null);

    if (!data) {
      return;
    }

    await fileUploadMutation.mutateAsync(data, {
      onError: (error) => {
        setUploadError(handleApiError(error));
        form.resetField("files");
      },
      onSuccess: (uploadResponse) => setUploadResponse(uploadResponse),
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
        onError: (e) => setUploadError(handleApiError(e)),
        onSuccess: (compId) => {
          fileStatsContext.set(
            compId,
            Object.fromEntries(uploadResponse.map((f) => [f.fileHash, f.stats]))
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

  useEffect(() => {
    if (!uploadResponse) {
      return;
    }
    // Ignore the answer if the files or settings changed while it was loading.
    let isCurrent = true;
    const fileHashes = uploadResponse.map(({ fileHash }) => fileHash);
    void getMostSuitableMethod(fileHashes, watchPermissiveTypes).then(
      (method) => {
        if (isCurrent) {
          setMostSuitableMethod(method);
        }
      }
    );
    return () => {
      isCurrent = false;
    };
  }, [uploadResponse, watchPermissiveTypes]);

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
              disabled={!isUploaded}
            >
              Compute
            </Button>
            <Button
              type="button"
              title="Selection of empirical charge calculation method and its parameters."
              variant={"secondary"}
              disabled={!isUploaded}
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

          {mostSuitableMethod && (
            <>
              <Separator className="my-4" />

              <p className="text-sm text-black text-opacity-40">
                Most suitable method is{" "}
                <span className="font-bold">
                  {mostSuitableMethod?.method.name}
                </span>{" "}
                {mostSuitableMethod?.parameters ? (
                  <span>
                    {" "}
                    with{" "}
                    <span className="font-bold">
                      {mostSuitableMethod?.parameters?.fullName}
                    </span>{" "}
                    parameters.
                  </span>
                ) : (
                  "."
                )}
              </p>
            </>
          )}
        </form>
      </Form>
    </Card>
  );
};
