import { Selection } from "@acc/api/compute/types";
import { useFormContext } from "react-hook-form";

import { InfoTooltip } from "../setup/info-tooltip";
import { FormControl, FormField, FormItem, FormLabel } from "../ui/form";
import { RadioGroup, RadioGroupItem } from "../ui/radio-group";
import { Switch } from "../ui/switch";

// Each selection leaves out more of the structure than the one before.
const SELECTIONS: { value: Selection; label: string }[] = [
  { value: "all", label: "All atoms" },
  { value: "polymers-and-ligands", label: "Without water" },
  { value: "polymers", label: "Polymers only" },
];

export const AdvancedSettings = () => {
  const form = useFormContext();

  return (
    <div className="flex flex-col gap-4">
      <FormField
        control={form.control}
        name="settings.selection"
        render={({ field }) => (
          <FormItem className="flex flex-col gap-2 space-y-0">
            <FormLabel className="font-bold">
              Atoms of PDB/mmCIF files
              <InfoTooltip info="Without water, ligands and ions stay. Polymers are protein and nucleic acid chains; their modified residues stay too." />
            </FormLabel>
            <FormControl>
              <RadioGroup
                value={field.value}
                onValueChange={field.onChange}
                className="gap-2"
              >
                {SELECTIONS.map(({ value, label }) => (
                  <FormItem
                    key={value}
                    className="flex items-center gap-2 space-y-0"
                  >
                    <FormControl>
                      <RadioGroupItem value={value} />
                    </FormControl>
                    <FormLabel className="font-normal">{label}</FormLabel>
                  </FormItem>
                ))}
              </RadioGroup>
            </FormControl>
          </FormItem>
        )}
      />
      <FormField
        control={form.control}
        name="settings.permissiveTypes"
        render={({ field }) => (
          <FormItem className="flex gap-2 items-center">
            <FormControl>
              <Switch checked={field.value} onCheckedChange={field.onChange} />
            </FormControl>
            <FormLabel className="font-bold">
              Permissive types
              <InfoTooltip info="Use similar parameters for similar atom/bond types if no exact match is found." />
            </FormLabel>
          </FormItem>
        )}
      />
    </div>
  );
};
