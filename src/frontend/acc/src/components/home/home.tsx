import { Banner } from "@acc/components/home/banner";
import { About } from "@acc/components/home/sections/about";
import { Citing } from "@acc/components/home/sections/citing";
import { Compute } from "@acc/components/home/sections/compute";
import { Elixir } from "@acc/components/home/sections/elixir";
import { Examples } from "@acc/components/home/sections/examples";
import { License } from "@acc/components/home/sections/license";
import { ScrollArea } from "@acc/components/ui/scroll-area";

export const Home = () => {
  return (
    <main className="mx-auto w-full selection:text-white selection:bg-primary">
      <ScrollArea type="auto">
        <Banner />
        <Compute />
        <About />
        <Examples />
        <Citing />
        <License />
        <Elixir />
      </ScrollArea>
    </main>
  );
};
