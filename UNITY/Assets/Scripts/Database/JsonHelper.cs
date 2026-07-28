// opencode: 2026-06-29 - JsonUtility top-level array 파싱 보조. review-fix(메인) 2026-06-29.
// JsonHelper.cs — Unity JsonUtility는 top-level JSON 배열도, 제네릭 타입도 직접 파싱하지 못한다.
// 따라서 호출부는 타입별 비제네릭 wrapper(EventRowArray 등)로 FromJson 하고,
// 이 헬퍼는 빈/널 가드 + {"rows":...} 래핑 문자열만 만들어준다(제네릭 ArrayWrapper<T>는 런타임 미동작이라 폐기).
namespace URHYNIX.ControlRoom.Database
{
    public static class JsonHelper
    {
        // PostgREST 응답(top-level 배열)을 비제네릭 wrapper가 파싱할 수 있게 {"rows":[...]}로 감싼다.
        public static string WrapRows(string json)
        {
            if (string.IsNullOrEmpty(json) || json == "[]") return "{\"rows\":[]}";
            return "{\"rows\":" + json + "}";
        }
    }
}
