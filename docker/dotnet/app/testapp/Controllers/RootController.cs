using System.Linq;
using Microsoft.AspNetCore.Mvc;

namespace TestAppDotnet.Controllers
{
	[Route("/")]
	[ApiController]
	public class RootController : ControllerBase
	{
		[HttpGet()]
		public ActionResult<string> Get() => "OK";
	}
}
