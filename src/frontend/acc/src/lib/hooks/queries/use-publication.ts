import { Method } from "@acc/api/methods/types";
import { Parameters } from "@acc/api/parameters/types";
import { useQuery } from "@tanstack/react-query";

export const usePublicationQuery = (data?: Parameters | Method) => {
  return useQuery({
    queryKey: ["publication", data?.internalName, data?.publication],
    queryFn: async () => {
      const { default: publicationData } = await import(
        "@acc/assets/publication_info.json"
      );
      if (data?.publication && data.publication in publicationData) {
        return publicationData[
          data.publication as keyof typeof publicationData
        ];
      } else {
        return "";
      }
    },
  });
};
