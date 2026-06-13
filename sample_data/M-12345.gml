<?xml version="1.0" encoding="UTF-8"?>
<!--
  Örnek MAKS CityGML LoD4 dosyası — Türkiye TAKBİS formatı
  EPSG:5254 (TUREF / TM30) — Marmara/İstanbul bölgesi
  Yapı: 2 bağımsız bölüm (BB-001: zemin kat 3+1, BB-002: 1.kat 2+1)
  Bu dosya test amaçlıdır; tüm koordinatlar sentetiktir.
-->
<CityModel
  xmlns="http://www.opengis.net/citygml/2.0"
  xmlns:bldg="http://www.opengis.net/citygml/building/2.0"
  xmlns:gen="http://www.opengis.net/citygml/generics/2.0"
  xmlns:gml="http://www.opengis.net/gml"
  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
  xsi:schemaLocation="http://www.opengis.net/citygml/2.0 http://schemas.opengis.net/citygml/2.0/cityGMLBase.xsd">

  <gml:name>M-12345 Örnek Apartman</gml:name>
  <gml:boundedBy>
    <gml:Envelope srsName="urn:ogc:def:crs:EPSG::5254" srsDimension="3">
      <gml:lowerCorner>471250.0 4205798.0 42.0</gml:lowerCorner>
      <gml:upperCorner>471270.0 4205820.0 51.8</gml:upperCorner>
    </gml:Envelope>
  </gml:boundedBy>

  <cityObjectMember>
    <bldg:Building gml:id="BINA-12345">
      <gml:name>Örnek Apartman M12345</gml:name>

      <!-- ── Bağımsız Bölüm 1: Zemin Kat (3+1) ─────────────────────── -->
      <bldg:consistsOfBuildingPart>
        <bldg:BuildingPart gml:id="BB-001">
          <gen:stringAttribute name="bagimsizbölüm_no">
            <gen:value>BB-001</gen:value>
          </gen:stringAttribute>

          <!-- Hol -->
          <bldg:interiorRoom>
            <bldg:Room gml:id="room-hol-001">
              <gml:name>Hol</gml:name>
              <gen:stringAttribute name="partUsageCode">
                <gen:value>hol</gen:value>
              </gen:stringAttribute>
              <gen:intAttribute name="floor">
                <gen:value>0</gen:value>
              </gen:intAttribute>
              <bldg:lod4MultiSurface>
                <gml:MultiSurface srsName="urn:ogc:def:crs:EPSG::5254" srsDimension="3">
                  <gml:surfaceMember>
                    <gml:Polygon>
                      <gml:exterior>
                        <gml:LinearRing>
                          <gml:posList srsDimension="3">
                            471252.0 4205798.0 42.0
                            471252.0 4205801.0 42.0
                            471265.0 4205801.0 42.0
                            471265.0 4205798.0 42.0
                            471252.0 4205798.0 42.0
                          </gml:posList>
                        </gml:LinearRing>
                      </gml:exterior>
                    </gml:Polygon>
                  </gml:surfaceMember>
                </gml:MultiSurface>
              </bldg:lod4MultiSurface>
            </bldg:Room>
          </bldg:interiorRoom>

          <!-- Salon -->
          <bldg:interiorRoom>
            <bldg:Room gml:id="room-salon-001">
              <gml:name>Salon</gml:name>
              <gen:stringAttribute name="partUsageCode">
                <gen:value>salon</gen:value>
              </gen:stringAttribute>
              <gen:intAttribute name="floor">
                <gen:value>0</gen:value>
              </gen:intAttribute>
              <bldg:lod4MultiSurface>
                <gml:MultiSurface srsName="urn:ogc:def:crs:EPSG::5254" srsDimension="3">
                  <gml:surfaceMember>
                    <gml:Polygon>
                      <gml:exterior>
                        <gml:LinearRing>
                          <gml:posList srsDimension="3">
                            471252.0 4205801.0 42.0
                            471252.0 4205810.0 42.0
                            471260.0 4205810.0 42.0
                            471260.0 4205801.0 42.0
                            471252.0 4205801.0 42.0
                          </gml:posList>
                        </gml:LinearRing>
                      </gml:exterior>
                    </gml:Polygon>
                  </gml:surfaceMember>
                </gml:MultiSurface>
              </bldg:lod4MultiSurface>
            </bldg:Room>
          </bldg:interiorRoom>

          <!-- Mutfak -->
          <bldg:interiorRoom>
            <bldg:Room gml:id="room-mutfak-001">
              <gml:name>Mutfak</gml:name>
              <gen:stringAttribute name="partUsageCode">
                <gen:value>mutfak</gen:value>
              </gen:stringAttribute>
              <gen:intAttribute name="floor">
                <gen:value>0</gen:value>
              </gen:intAttribute>
              <bldg:lod4MultiSurface>
                <gml:MultiSurface srsName="urn:ogc:def:crs:EPSG::5254" srsDimension="3">
                  <gml:surfaceMember>
                    <gml:Polygon>
                      <gml:exterior>
                        <gml:LinearRing>
                          <gml:posList srsDimension="3">
                            471260.0 4205801.0 42.0
                            471260.0 4205807.0 42.0
                            471265.0 4205807.0 42.0
                            471265.0 4205801.0 42.0
                            471260.0 4205801.0 42.0
                          </gml:posList>
                        </gml:LinearRing>
                      </gml:exterior>
                    </gml:Polygon>
                  </gml:surfaceMember>
                </gml:MultiSurface>
              </bldg:lod4MultiSurface>
            </bldg:Room>
          </bldg:interiorRoom>

          <!-- Yatak Odası -->
          <bldg:interiorRoom>
            <bldg:Room gml:id="room-yatak1-001">
              <gml:name>Yatak Odası</gml:name>
              <gen:stringAttribute name="partUsageCode">
                <gen:value>yatakodasi</gen:value>
              </gen:stringAttribute>
              <gen:intAttribute name="floor">
                <gen:value>0</gen:value>
              </gen:intAttribute>
              <bldg:lod4MultiSurface>
                <gml:MultiSurface srsName="urn:ogc:def:crs:EPSG::5254" srsDimension="3">
                  <gml:surfaceMember>
                    <gml:Polygon>
                      <gml:exterior>
                        <gml:LinearRing>
                          <gml:posList srsDimension="3">
                            471252.0 4205810.0 42.0
                            471252.0 4205816.0 42.0
                            471258.0 4205816.0 42.0
                            471258.0 4205810.0 42.0
                            471252.0 4205810.0 42.0
                          </gml:posList>
                        </gml:LinearRing>
                      </gml:exterior>
                    </gml:Polygon>
                  </gml:surfaceMember>
                </gml:MultiSurface>
              </bldg:lod4MultiSurface>
            </bldg:Room>
          </bldg:interiorRoom>

          <!-- Çocuk Odası -->
          <bldg:interiorRoom>
            <bldg:Room gml:id="room-cocuk-001">
              <gml:name>Çocuk Odası</gml:name>
              <gen:stringAttribute name="partUsageCode">
                <gen:value>cocukodasi</gen:value>
              </gen:stringAttribute>
              <gen:intAttribute name="floor">
                <gen:value>0</gen:value>
              </gen:intAttribute>
              <bldg:lod4MultiSurface>
                <gml:MultiSurface srsName="urn:ogc:def:crs:EPSG::5254" srsDimension="3">
                  <gml:surfaceMember>
                    <gml:Polygon>
                      <gml:exterior>
                        <gml:LinearRing>
                          <gml:posList srsDimension="3">
                            471258.0 4205810.0 42.0
                            471258.0 4205816.0 42.0
                            471265.0 4205816.0 42.0
                            471265.0 4205810.0 42.0
                            471258.0 4205810.0 42.0
                          </gml:posList>
                        </gml:LinearRing>
                      </gml:exterior>
                    </gml:Polygon>
                  </gml:surfaceMember>
                </gml:MultiSurface>
              </bldg:lod4MultiSurface>
            </bldg:Room>
          </bldg:interiorRoom>

          <!-- Banyo -->
          <bldg:interiorRoom>
            <bldg:Room gml:id="room-banyo-001">
              <gml:name>Banyo</gml:name>
              <gen:stringAttribute name="partUsageCode">
                <gen:value>banyo</gen:value>
              </gen:stringAttribute>
              <gen:intAttribute name="floor">
                <gen:value>0</gen:value>
              </gen:intAttribute>
              <bldg:lod4MultiSurface>
                <gml:MultiSurface srsName="urn:ogc:def:crs:EPSG::5254" srsDimension="3">
                  <gml:surfaceMember>
                    <gml:Polygon>
                      <gml:exterior>
                        <gml:LinearRing>
                          <gml:posList srsDimension="3">
                            471265.0 4205807.0 42.0
                            471265.0 4205812.0 42.0
                            471269.0 4205812.0 42.0
                            471269.0 4205807.0 42.0
                            471265.0 4205807.0 42.0
                          </gml:posList>
                        </gml:LinearRing>
                      </gml:exterior>
                    </gml:Polygon>
                  </gml:surfaceMember>
                </gml:MultiSurface>
              </bldg:lod4MultiSurface>
            </bldg:Room>
          </bldg:interiorRoom>

          <!-- WC -->
          <bldg:interiorRoom>
            <bldg:Room gml:id="room-wc-001">
              <gml:name>WC</gml:name>
              <gen:stringAttribute name="partUsageCode">
                <gen:value>wc</gen:value>
              </gen:stringAttribute>
              <gen:intAttribute name="floor">
                <gen:value>0</gen:value>
              </gen:intAttribute>
              <bldg:lod4MultiSurface>
                <gml:MultiSurface srsName="urn:ogc:def:crs:EPSG::5254" srsDimension="3">
                  <gml:surfaceMember>
                    <gml:Polygon>
                      <gml:exterior>
                        <gml:LinearRing>
                          <gml:posList srsDimension="3">
                            471265.0 4205812.0 42.0
                            471265.0 4205816.0 42.0
                            471269.0 4205816.0 42.0
                            471269.0 4205812.0 42.0
                            471265.0 4205812.0 42.0
                          </gml:posList>
                        </gml:LinearRing>
                      </gml:exterior>
                    </gml:Polygon>
                  </gml:surfaceMember>
                </gml:MultiSurface>
              </bldg:lod4MultiSurface>
            </bldg:Room>
          </bldg:interiorRoom>

        </bldg:BuildingPart>
      </bldg:consistsOfBuildingPart>

      <!-- ── Bağımsız Bölüm 2: 1. Kat (2+1) ────────────────────────── -->
      <bldg:consistsOfBuildingPart>
        <bldg:BuildingPart gml:id="BB-002">
          <gen:stringAttribute name="bagimsizbölüm_no">
            <gen:value>BB-002</gen:value>
          </gen:stringAttribute>

          <!-- Salon -->
          <bldg:interiorRoom>
            <bldg:Room gml:id="room-salon-002">
              <gml:name>Salon</gml:name>
              <gen:stringAttribute name="partUsageCode">
                <gen:value>salon</gen:value>
              </gen:stringAttribute>
              <gen:intAttribute name="floor">
                <gen:value>1</gen:value>
              </gen:intAttribute>
              <bldg:lod4MultiSurface>
                <gml:MultiSurface srsName="urn:ogc:def:crs:EPSG::5254" srsDimension="3">
                  <gml:surfaceMember>
                    <gml:Polygon>
                      <gml:exterior>
                        <gml:LinearRing>
                          <gml:posList srsDimension="3">
                            471252.0 4205801.0 45.0
                            471252.0 4205810.0 45.0
                            471262.0 4205810.0 45.0
                            471262.0 4205801.0 45.0
                            471252.0 4205801.0 45.0
                          </gml:posList>
                        </gml:LinearRing>
                      </gml:exterior>
                    </gml:Polygon>
                  </gml:surfaceMember>
                </gml:MultiSurface>
              </bldg:lod4MultiSurface>
            </bldg:Room>
          </bldg:interiorRoom>

          <!-- Yatak Odası -->
          <bldg:interiorRoom>
            <bldg:Room gml:id="room-yatak1-002">
              <gml:name>Yatak Odası</gml:name>
              <gen:stringAttribute name="partUsageCode">
                <gen:value>yatakodasi</gen:value>
              </gen:stringAttribute>
              <gen:intAttribute name="floor">
                <gen:value>1</gen:value>
              </gen:intAttribute>
              <bldg:lod4MultiSurface>
                <gml:MultiSurface srsName="urn:ogc:def:crs:EPSG::5254" srsDimension="3">
                  <gml:surfaceMember>
                    <gml:Polygon>
                      <gml:exterior>
                        <gml:LinearRing>
                          <gml:posList srsDimension="3">
                            471252.0 4205810.0 45.0
                            471252.0 4205818.0 45.0
                            471260.0 4205818.0 45.0
                            471260.0 4205810.0 45.0
                            471252.0 4205810.0 45.0
                          </gml:posList>
                        </gml:LinearRing>
                      </gml:exterior>
                    </gml:Polygon>
                  </gml:surfaceMember>
                </gml:MultiSurface>
              </bldg:lod4MultiSurface>
            </bldg:Room>
          </bldg:interiorRoom>

          <!-- Mutfak -->
          <bldg:interiorRoom>
            <bldg:Room gml:id="room-mutfak-002">
              <gml:name>Mutfak</gml:name>
              <gen:stringAttribute name="partUsageCode">
                <gen:value>mutfak</gen:value>
              </gen:stringAttribute>
              <gen:intAttribute name="floor">
                <gen:value>1</gen:value>
              </gen:intAttribute>
              <bldg:lod4MultiSurface>
                <gml:MultiSurface srsName="urn:ogc:def:crs:EPSG::5254" srsDimension="3">
                  <gml:surfaceMember>
                    <gml:Polygon>
                      <gml:exterior>
                        <gml:LinearRing>
                          <gml:posList srsDimension="3">
                            471262.0 4205801.0 45.0
                            471262.0 4205808.0 45.0
                            471268.0 4205808.0 45.0
                            471268.0 4205801.0 45.0
                            471262.0 4205801.0 45.0
                          </gml:posList>
                        </gml:LinearRing>
                      </gml:exterior>
                    </gml:Polygon>
                  </gml:surfaceMember>
                </gml:MultiSurface>
              </bldg:lod4MultiSurface>
            </bldg:Room>
          </bldg:interiorRoom>

          <!-- Banyo -->
          <bldg:interiorRoom>
            <bldg:Room gml:id="room-banyo-002">
              <gml:name>Banyo</gml:name>
              <gen:stringAttribute name="partUsageCode">
                <gen:value>banyo</gen:value>
              </gen:stringAttribute>
              <gen:intAttribute name="floor">
                <gen:value>1</gen:value>
              </gen:intAttribute>
              <bldg:lod4MultiSurface>
                <gml:MultiSurface srsName="urn:ogc:def:crs:EPSG::5254" srsDimension="3">
                  <gml:surfaceMember>
                    <gml:Polygon>
                      <gml:exterior>
                        <gml:LinearRing>
                          <gml:posList srsDimension="3">
                            471260.0 4205810.0 45.0
                            471260.0 4205815.0 45.0
                            471265.0 4205815.0 45.0
                            471265.0 4205810.0 45.0
                            471260.0 4205810.0 45.0
                          </gml:posList>
                        </gml:LinearRing>
                      </gml:exterior>
                    </gml:Polygon>
                  </gml:surfaceMember>
                </gml:MultiSurface>
              </bldg:lod4MultiSurface>
            </bldg:Room>
          </bldg:interiorRoom>

          <!-- Balkon -->
          <bldg:interiorRoom>
            <bldg:Room gml:id="room-balkon-002">
              <gml:name>Balkon</gml:name>
              <gen:stringAttribute name="partUsageCode">
                <gen:value>balkon</gen:value>
              </gen:stringAttribute>
              <gen:intAttribute name="floor">
                <gen:value>1</gen:value>
              </gen:intAttribute>
              <bldg:lod4MultiSurface>
                <gml:MultiSurface srsName="urn:ogc:def:crs:EPSG::5254" srsDimension="3">
                  <gml:surfaceMember>
                    <gml:Polygon>
                      <gml:exterior>
                        <gml:LinearRing>
                          <gml:posList srsDimension="3">
                            471260.0 4205815.0 45.0
                            471260.0 4205820.0 45.0
                            471268.0 4205820.0 45.0
                            471268.0 4205815.0 45.0
                            471260.0 4205815.0 45.0
                          </gml:posList>
                        </gml:LinearRing>
                      </gml:exterior>
                    </gml:Polygon>
                  </gml:surfaceMember>
                </gml:MultiSurface>
              </bldg:lod4MultiSurface>
            </bldg:Room>
          </bldg:interiorRoom>

        </bldg:BuildingPart>
      </bldg:consistsOfBuildingPart>

    </bldg:Building>
  </cityObjectMember>
</CityModel>
