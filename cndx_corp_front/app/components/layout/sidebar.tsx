import { cn } from "~/lib/utils";
import { CndxCorpNav } from "~/components/cndx-corp-nav";
import { useMenu } from "./menu-provider";
import sidebar_styles from '~/styles/sidebarMenu.module.css';


export default function Sidebar() {
  const { navItems } = useMenu();
  return (
    <nav className={cn(`relative hidden w-72 border-r pt-16 lg:block`)}>
      <div className={`${sidebar_styles.sidebar} `}>
        <div className="space-y-4 py-4">
          <div className="px-3 py-2">
            <div className="space-y-1">
              <h2 className="mb-2 px-4 text-xl font-semibold tracking-tight">
                EP法人営業部
              </h2>
              <CndxCorpNav items={navItems} />
            </div>
          </div>
        </div>
      </div>
    </nav>
  );
}
