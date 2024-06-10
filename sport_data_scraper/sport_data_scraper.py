import argparse
from sport_data_scraper import scraper, open_list_of_urls

def check_for_days_arguments():
    pass

def main():
    parser=argparse.ArgumentParser(description="Help menu for the sport data scraper")

    # The sub-command's string will be stored in "parsed_arguments.cmd"
    subparser = parser.add_subparsers(dest="cmd") 

    subparser_scraper = subparser.add_parser('scraper')
    
    subparser_scraper.add_argument("--day", "--d", default=0, choices=[0,1,2,3,4,5,6], type=int, help="Argument for scraping specified day data: 0 = today, 1 = tommorow...")
    subparser_scraper.add_argument("--overNumOfGoals", "--o", default=5, type=int, help="Sets the over goal number threshold. Default = 5")
    subparser_scraper.add_argument("--lessNumOfGoals", "--l", default=3, type=int, help="Sets the under goal number threshold. Default = 3")
    subparser_scraper.add_argument("--matchCount", "--m", default=4, type=int, help="Sets the minimum number of matches that satisfy the threshold")
    subparser_scraper.add_argument("--nbttswin", "--nbttsw", action='store_true', help="Combines nbtts and win result")
    subparser_scraper.add_argument("--forceFlag", "--f", action='store_true', help="Combines nbtts and win result")

    subparser_scraper = subparser.add_parser('open', formatter_class=argparse.RawTextHelpFormatter)
    subparser_scraper.add_argument("--openType", "--t", nargs = '*', default="o", choices=["o","u","btts","nbtts","w","nbttsw"],
    help= 
    """
    Sets the opening type:
        o = over total number of goals
        u = under total number of goals
        btts = both team to score
        nbtts = no both team to score
        w = a team wins consectutively
        nbttsw = nbtts & w
    """)

    args=parser.parse_args()
    print(args)

    if args.cmd == "scraper" or args.cmd == None:
        scraper.runScraper(args.day, args.overNumOfGoals, args.lessNumOfGoals, args.matchCount, args.nbttswin, args.forceFlag)

    if args.cmd == "open":
        open_list_of_urls.runOpen(args.openType)

if __name__ == "__main__":
    main()

